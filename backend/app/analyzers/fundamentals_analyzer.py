import requests
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
    usd_pegged = ['XAU', 'XAG', 'GC=F', 'SI=F', 'WTI', 'BZ=F', 'CRUDE', 'SPX', '^GSPC', 'SPX500', 'US30', 'NAS100']
    for pegged in usd_pegged:
        if pegged in symbol:
            currencies.append("USD")
            
    # Include generic USD mapping for safety if it ends with USD or is a US stock (1-5 chars)
    if symbol.endswith("USD") or (len(symbol) <= 5 and not currencies):
        currencies.append("USD")
        
    return list(set(currencies))


def analyze_fundamentals(symbol: str) -> FundamentalsAnalysis:
    """Check macro events and corporate earnings."""
    now = datetime.now()
    cutoff_48h = now + timedelta(hours=48)

    events = []
    has_high_impact = False
    event_timestamps = []
    minutes_to_next: Optional[int] = None

    # 1. Economic Calendar (Macro Events)
    currencies = _detect_relevant_currencies(symbol)
    if currencies:
        calendar = _get_forex_calendar()
        for item in calendar:
            impact = item.get('impact', '')
            country = item.get('country', '')
            date_str = item.get('date', '')
            title = item.get('title', '')

            if impact == 'High' and country in currencies:
                try:
                    # Ensure date_str is a string and not a tuple
                    if isinstance(date_str, tuple):
                        date_str = str(date_str[0] if date_str else '')
                    elif not isinstance(date_str, str):
                        date_str = str(date_str)
                    
                    # Parse datetime safely
                    dt = datetime.fromisoformat(date_str[:19])
                    if now <= dt <= cutoff_48h:
                        hours_away = int((dt - now).total_seconds() // 3600)
                        mins_away = int((dt - now).total_seconds() // 60)
                        events.append(f"🔴 [{country}] {title} ({hours_away}h away)")
                        has_high_impact = True
                        event_timestamps.append({
                            "event": f"[{country}] {title}",
                            "time_utc": dt.strftime('%Y-%m-%dT%H:%M:%S'),
                            "impact": "HIGH"
                        })
                        if minutes_to_next is None or mins_away < minutes_to_next:
                            minutes_to_next = mins_away
                except Exception:
                    pass

    # Pre-event risk reduction logic
    risk_reduction_active = False
    pre_event_caution = False
    position_multiplier = 1.0

    if minutes_to_next is not None:
        if minutes_to_next <= 60:
            risk_reduction_active = True
            position_multiplier = 0.5
        elif minutes_to_next <= 1440:  # 24 hours
            pre_event_caution = True
            position_multiplier = 0.75

    # Build description
    if not events:
        desc = "No major high-impact macro events or earnings in the next 48 hours. Clear fundamental skies."
    else:
        desc = "WARNING! High volatility expected: " + " | ".join(events)

    from app.models import EventEntry
    return FundamentalsAnalysis(
        has_high_impact_events=has_high_impact,
        events=events,
        description=desc,
        event_timestamps=[EventEntry(**e) for e in event_timestamps],
        risk_reduction_active=risk_reduction_active,
        recommended_position_multiplier=position_multiplier,
        pre_event_caution=pre_event_caution,
        minutes_to_next_event=minutes_to_next
    )
