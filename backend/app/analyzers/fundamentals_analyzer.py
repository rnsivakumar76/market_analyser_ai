import requests
import yfinance as yf
from datetime import datetime, timedelta
import logging
from typing import List, Optional
from pydantic import BaseModel
from app.models import FundamentalsAnalysis

logger = logging.getLogger(__name__)

# Cache calendar to avoid spamming ForexFactory
_ff_cache: dict = {"timestamp": None, "data": None}

def _get_forex_calendar() -> List[dict]:
    """Fetch 'This Week's' high-impact economic calendar from ForexFactory public JSON."""
    global _ff_cache
    
    # 1 hour cache
    if _ff_cache["timestamp"] and _ff_cache["data"] is not None:
        if (datetime.now() - _ff_cache["timestamp"]).total_seconds() < 3600:
            return _ff_cache["data"]
            
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get('https://nfs.faireconomy.media/ff_calendar_thisweek.json', headers=headers, timeout=5)
        if r.status_code == 200:
            _ff_cache["data"] = r.json()
            _ff_cache["timestamp"] = datetime.now()
            return _ff_cache["data"]
    except Exception as e:
        logger.error(f"Failed to fetch economic calendar: {e}")
        
    return []


def _detect_relevant_currencies(symbol: str) -> List[str]:
    """Map a trading symbol to relevant macroeconomic currencies."""
    symbol = symbol.upper()
    currencies = []
    
    # Forex pairs (e.g. EURUSD)
    if len(symbol) == 6 and not symbol.endswith('=F') and not symbol.endswith('=X'):
        currencies.extend([symbol[:3], symbol[3:]])
    
    # Commodities / Indices heavily pegged to USD
    usd_pegged = ['XAU', 'XAG', 'GC=F', 'SI=F', 'BCO', 'BZ=F', 'CRUDE', 'SPX', '^GSPC', 'SPX500', 'US30', 'NAS100']
    for pegged in usd_pegged:
        if pegged in symbol:
            currencies.append("USD")
            
    # Include generic USD mapping for safety if it ends with USD
    if symbol.endswith("USD"):
        currencies.append("USD")
        
    return list(set(currencies))


def analyze_fundamentals(symbol: str, yf_symbol: str) -> FundamentalsAnalysis:
    """Check macro events and corporate earnings."""
    now = datetime.now()
    cutoff_48h = now + timedelta(hours=48)
    
    events = []
    has_high_impact = False
    
    # 1. Economic Calendar (Macro Events)
    currencies = _detect_relevant_currencies(symbol)
    if currencies:
        calendar = _get_forex_calendar()
        for item in calendar:
            impact = item.get('impact', '')
            country = item.get('country', '')
            date_str = item.get('date', '')
            title = item.get('title', '')
            
            # High impact red folder events only
            if impact == 'High' and country in currencies:
                try:
                    # e.g., "2023-09-06T10:00:00-04:00"
                    event_date_str = date_str.split("-0")[0] if "-" in date_str[11:] else date_str
                    event_date_str = event_date_str.split("+")[0]
                    # Attempt naive parsing (ForexFactory JSON often strips tz but has it at end, we just use raw ISO prefix)
                    dt = datetime.fromisoformat(date_str[:19])
                    
                    if now <= dt <= cutoff_48h:
                        events.append(f"🔴 [{country}] {title} ({(dt - now).resolution}/{(dt - now).seconds//3600}h away)")
                        has_high_impact = True
                except Exception:
                    pass
    
    # 2. Corporate Earnings (Stocks)
    # Exclude obvious non-stocks
    if len(symbol) <= 5 and not any(sym in symbol for sym in ['XAU', 'XAG', 'EUR', 'USD', 'JPY', 'GBP', 'BCO', 'SPX']):
        try:
            ticker = yf.Ticker(yf_symbol)
            cal = ticker.calendar
            
            if isinstance(cal, dict) and 'Earnings Date' in cal:
                earnings_dates = cal['Earnings Date']
                if not isinstance(earnings_dates, list):
                    earnings_dates = [earnings_dates]
                    
                for e_date in earnings_dates:
                    if hasattr(e_date, 'date'):
                        e_date = e_date.date()
                    # If it's datetime.date format
                    if isinstance(e_date, datetime):
                        e_date = e_date.date()
                        
                    days_away = (e_date - now.date()).days
                    if 0 <= days_away <= 7:
                        has_high_impact = True
                        events.append(f"📊 Earnings Report in {days_away} days ({e_date})!")
                    elif days_away < 0 and days_away > -3:
                        events.append(f"📊 Earnings Report just occurred ({abs(days_away)} days ago). Proceed with caution.")
        except Exception as e:
            logger.debug(f"Could not fetch earnings for {symbol}: {e}")

    # Build description
    if not events:
        desc = "No major high-impact macro events or earnings in the next 48 hours. Clear fundamental skies."
    else:
        desc = "WARNING! High volatility expected: " + " | ".join(events)
        
    return FundamentalsAnalysis(
        has_high_impact_events=has_high_impact,
        events=events,
        description=desc
    )
