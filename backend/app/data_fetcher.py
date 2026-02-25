import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import urllib3
import requests
import random
import numpy as np
import os
import logging
from .alpha_vantage_fetcher import AlphaVantageFetcher
from .twelvedata_fetcher import TwelveDataFetcher
from .fmp_fetcher import FMPFetcher

# Setup logger
logger = logging.getLogger(__name__)

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
    interval: str = "1d",
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a given symbol.
    Intervals: 1h, 4h, 1d, 1wk, 1mo
    """
    # MANDATORY: Twelve Data as Primary Professional Source
    td = get_td_fetcher()
    if td.api_key and td.api_key != 'YOUR_API_KEY_HERE':
        try:
            logger.info(f"PRO MODE: Strictly using Twelve Data for {symbol} ({interval})...")
            # Map Twelve Data intervals
            td_interval = "1day"
            if interval == "1h": td_interval = "1h"
            elif interval == "4h": td_interval = "4h"
            elif interval == "1wk": td_interval = "1week"
            elif interval == "1mo": td_interval = "1month"

            df = td.fetch_historical_data(symbol, days=days, interval=td_interval)
            if not df.empty:
                logger.info(f"✅ Twelve Data Success for {symbol}")
                return df
        except Exception as e:
            logger.error(f"❌ Twelve Data professional fetch failed: {e}")
            # If Twelve Data is the PRIMARY and it fails, we should NOT silently fallback to low-quality data
            # unless Twelve Data is completely down or doesn't support the symbol.
            if "not found" in str(e).lower() or "delisted" in str(e).lower():
                logger.warning("Symbol not found in Twelve Data, trying fallback...")
            else:
                raise ValueError(f"Twelve Data primary fetch failed for {symbol}: {e}")

    # Check for mock mode
    if os.getenv('USE_MOCK_DATA', 'false').lower() == 'true':
        print(f"🛠️ Using MOCK DATA for {symbol} ({interval})")
        df = generate_mock_data(symbol, days)
        # Mock data is daily, resample if needed
        if interval == "1wk":
            return df.resample('W').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
        if interval == "1mo":
            return df.resample('ME').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
        return df

    # Priority 1: Professional Paid APIs (If keys are configured)
    # Check for Twelve Data
    td = get_td_fetcher()
    if td.api_key and td.api_key != 'YOUR_API_KEY_HERE':
        try:
            logger.info(f"Professional Priority: Trying Twelve Data for {symbol} ({interval})...")
            # Map Twelve Data intervals
            td_interval = "1day"
            if interval == "1h": td_interval = "1h"
            elif interval == "4h": td_interval = "4h"
            elif interval == "1wk": td_interval = "1week"
            elif interval == "1mo": td_interval = "1month"

            df = td.fetch_historical_data(symbol, days=days, interval=td_interval)
            if not df.empty:
                logger.info(f"✅ Twelve Data Success for {symbol}")
                return df
        except Exception as e:
            logger.warning(f"⚠️ Twelve Data failed for {symbol}: {e}")

    # Check for FMP
    fmp = get_fmp_fetcher()
    if fmp.api_key and fmp.api_key != 'YOUR_API_KEY_HERE':
        try:
            logger.info(f"Professional Priority: Trying FMP for {symbol}...")
            # FMP primary usage is daily in this implementation
            if interval == "1d":
                df = fmp.fetch_historical_data(symbol, days=days)
                if not df.empty:
                    logger.info(f"✅ FMP Success for {symbol}")
                    return df
        except Exception as e:
            logger.warning(f"⚠️ FMP failed for {symbol}: {e}")

    # Map interval for yfinance (fallback)
    yf_interval = interval
    resample_to_4h = False
    if interval == "4h":
        yf_interval = "1h"
        resample_to_4h = True

    # Priority 2: yfinance (Free/Community source)
    yf_symbols = _get_yf_symbols(symbol)
    for yf_sym in yf_symbols:
        try:
            logger.info(f"Fallback: Trying yfinance for {symbol} (as {yf_sym}, {interval})...")
            if end_date is None:
                end_date = datetime.now()
            
            start_date = end_date - timedelta(days=days)
            
            # Use a fresh ticker object and avoid session caching if possible
            ticker = yf.Ticker(yf_sym)
            df = ticker.history(start=start_date, end=end_date, interval=yf_interval)
            
            if not df.empty:
                if resample_to_4h:
                    df = df.resample('4H').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
                logger.info(f"✅ yfinance success for {symbol} as {yf_sym}")
                return df
        except Exception as e:
            logger.error(f"❌ yfinance failed for {symbol} as {yf_sym}: {e}")
            continue

    # Priority 3: Alpha Vantage (often has strict rate limits)
    if interval == "1d":
        try:
            logger.info(f"Final Fallback: Trying Alpha Vantage for {symbol}...")
            data = get_av_fetcher().fetch_historical_data(symbol, days)
            if not data.empty:
                logger.info(f"✅ Alpha Vantage success for {symbol}")
                return data
        except Exception as e:
            logger.error(f"❌ Alpha Vantage failed for {symbol}: {e}")

    # If we need weekly/monthly but only have daily from other fetchers
    if interval in ["1wk", "1mo"]:
        try:
            daily_data = fetch_historical_data(symbol, days, interval="1d")
            resample_rule = 'W' if interval == "1wk" else 'ME'
            return daily_data.resample(resample_rule).agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'})
        except:
            pass

    raise ValueError(f"Failed to fetch {interval} data for {symbol} from all sources")


def get_current_price(symbol: str) -> float:
    """Get the current/latest price for a symbol.
    
    If Twelve Data is configured, it is the MANDATORY primary source.
    Other sources (FMP, Alpha Vantage, yfinance) are only used if Twelve Data
    is not configured OR specifically fails to find the symbol.
    """
    mock_env = os.getenv('USE_MOCK_DATA', 'false').lower()
    if mock_env == 'true':
        mock_data = generate_mock_data(symbol, days=5)
        return float(mock_data['Close'].iloc[-1]) if not mock_data.empty else 100.0

    # MANDATORY: Twelve Data First for EVERYTHING
    td = get_td_fetcher()
    if td.api_key and td.api_key != 'YOUR_API_KEY_HERE':
        try:
            logger.info(f"PRO MODE: Strictly fetching current price for {symbol} from Twelve Data...")
            price = td.get_current_price(symbol)
            if price and price > 0:
                logger.info(f"✅ Twelve Data price for {symbol}: {price}")
                return price
        except Exception as e:
            logger.error(f"❌ Twelve Data current price failed: {e}")
            # Only fallback if valid reason (not a rate limit or API error)
            if "not found" not in str(e).lower() and "delisted" not in str(e).lower():
                raise ValueError(f"Twelve Data primary price fetch failed for {symbol}: {e}")

    # Fallback Priority for non-pro or if Twelve Data failed specifically on symbol existence
    # Try FMP/Paid APIs first for commodities, then yfinance
    PREFER_PAID_API = {'XAU', 'XAG', 'BCO', 'USDJPY', 'EURUSD', 'SPX', 'SPX500'}
    if symbol.upper() in PREFER_PAID_API:
        price = _try_paid_apis(symbol)
        if price: return price
        price = _try_yfinance_price(symbol)
        if price: return price
    else:
        # Standard yf -> paid flow for stocks
        price = _try_yfinance_price(symbol)
        if price: return price
        price = _try_paid_apis(symbol)
        if price: return price

    raise ValueError(f"Failed to get current price for {symbol} from all sources")


def _try_paid_apis(symbol: str) -> float | None:
    """Try Twelve Data, FMP, and Alpha Vantage in order."""
    # Twelve Data first (most reliable for commodities/forex)
    try:
        logger.info(f"Trying Twelve Data for current price of {symbol}...")
        price = get_td_fetcher().get_current_price(symbol)
        if price and price > 0:
            logger.info(f"✅ Twelve Data price for {symbol}: {price}")
            return price
    except Exception as e:
        logger.error(f"❌ Twelve Data price failed for {symbol}: {e}")

    # FMP second
    try:
        logger.info(f"Trying FMP for current price of {symbol}...")
        price = get_fmp_fetcher().get_current_price(symbol)
        if price and price > 0:
            logger.info(f"✅ FMP price for {symbol}: {price}")
            return price
    except Exception as e:
        logger.error(f"❌ FMP price failed for {symbol}: {e}")

    # Alpha Vantage third
    try:
        logger.info(f"Trying Alpha Vantage for current price of {symbol}...")
        price = get_av_fetcher().get_current_price(symbol)
        if price and price > 0:
            logger.info(f"✅ Alpha Vantage price for {symbol}: {price}")
            return price
    except Exception as e:
        logger.error(f"❌ Alpha Vantage price failed for {symbol}: {e}")

    return None


def _try_yfinance_price(symbol: str) -> float | None:
    """Try yfinance for current price using multiple strategies."""
    yf_symbols = _get_yf_symbols(symbol)
    for yf_sym in yf_symbols:
        try:
            logger.info(f"Trying yfinance for current price of {symbol} (as {yf_sym})...")
            ticker = yf.Ticker(yf_sym)
            
            # 1st: fast_info (near real-time)
            try:
                fi = ticker.fast_info
                if hasattr(fi, 'last_price') and fi.last_price and fi.last_price > 0:
                    price = float(fi.last_price)
                    logger.info(f"✅ yfinance fast_info price for {symbol} as {yf_sym}: {price}")
                    return price
            except Exception:
                pass
            
            # 2nd: info dict
            try:
                info = ticker.info
                for key in ['regularMarketPrice', 'currentPrice', 'ask', 'bid']:
                    if info.get(key) and info[key] > 0:
                        price = float(info[key])
                        logger.info(f"✅ yfinance info[{key}] price for {symbol} as {yf_sym}: {price}")
                        return price
            except Exception:
                pass
            
            # 3rd: 1-minute candle
            try:
                data = ticker.history(period="1d", interval="1m")
                if not data.empty:
                    price = float(data['Close'].iloc[-1])
                    logger.info(f"✅ yfinance 1m-candle price for {symbol} as {yf_sym}: {price}")
                    return price
            except Exception:
                pass
            
            # 4th: daily close (least accurate)
            data = ticker.history(period="1d")
            if data.empty:
                data = ticker.history(period="5d")
            if not data.empty:
                price = float(data['Close'].iloc[-1])
                logger.info(f"✅ yfinance daily-close fallback for {symbol} as {yf_sym}: {price}")
                return price
        except Exception as e:
            logger.error(f"❌ yfinance price failed for {symbol} as {yf_sym}: {e}")
            continue
    return None



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
