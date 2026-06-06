"""
Oil Market Context Analyzer
=============================
Provides three layers of oil-specific market intelligence:

  1. OVX (CBOE Crude Oil Volatility Index)  — via yfinance ^OVX, FREE
  2. EIA Weekly Crude Inventory Report       — via EIA API v2, FREE (key from env)
  3. OPEC+ Meeting Calendar                  — hardcoded schedule, zero cost

All three are combined into an OilMarketContext that gates position sizing
and adds explicit warnings when conditions are hostile for technical trading.
"""

import logging
import os
import requests
from datetime import datetime, timedelta, date
from typing import Optional, List

from ..models import OilMarketContext, OVXRegime, EIAInventoryReport, OpecWindow

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache — avoid spamming external APIs on every analysis refresh
# ---------------------------------------------------------------------------
_OVX_CACHE: dict = {"ts": 0, "data": None}
_EIA_CACHE: dict = {"ts": 0, "data": None}
_CACHE_TTL = 3600  # 1 hour


# ---------------------------------------------------------------------------
# OPEC+ Meeting Schedule  (update annually)
# Dates when OPEC+ ministerial meetings are scheduled
# ---------------------------------------------------------------------------
_OPEC_MEETINGS: List[date] = [
    date(2025, 6, 1),
    date(2025, 12, 5),
    date(2026, 3, 2),
    date(2026, 6, 1),
    date(2026, 12, 7),
]
_OPEC_WINDOW_DAYS = 5  # flag ±5 days around a meeting


# ---------------------------------------------------------------------------
# OVX — Oil Volatility Regime
# ---------------------------------------------------------------------------

def _fetch_ovx() -> Optional[float]:
    """Fetch latest OVX close via yfinance. Returns float or None."""
    import time as _time
    if _OVX_CACHE["ts"] and (_time.time() - _OVX_CACHE["ts"]) < _CACHE_TTL:
        return _OVX_CACHE["data"]
    try:
        import yfinance as yf
        tkr = yf.Ticker("^OVX")
        hist = tkr.history(period="5d", interval="1d")
        if hist is not None and not hist.empty:
            val = float(hist["Close"].dropna().iloc[-1])
            _OVX_CACHE["ts"] = _time.time()
            _OVX_CACHE["data"] = val
            logger.info(f"[OVX] Latest value: {val:.1f}")
            return val
    except Exception as e:
        logger.warning(f"[OVX] fetch failed: {e}")
    return None


def _classify_ovx(value: float) -> OVXRegime:
    """Map OVX value to a trading regime."""
    if value < 25:
        return OVXRegime(
            current_value=round(value, 1),
            regime="LOW",
            regime_label="Low Volatility",
            trading_implication="Normal volatility — standard position size appropriate.",
            size_multiplier=1.0,
        )
    elif value < 35:
        return OVXRegime(
            current_value=round(value, 1),
            regime="NORMAL",
            regime_label="Normal Volatility",
            trading_implication="Moderate volatility — use standard sizing with wider stops.",
            size_multiplier=1.0,
        )
    elif value < 50:
        return OVXRegime(
            current_value=round(value, 1),
            regime="ELEVATED",
            regime_label="Elevated Volatility",
            trading_implication="High oil volatility — reduce position to 60-70% of normal. Wider stops required.",
            size_multiplier=0.65,
        )
    else:
        return OVXRegime(
            current_value=round(value, 1),
            regime="EXTREME",
            regime_label="Extreme Volatility",
            trading_implication="Extreme volatility (geopolitical/supply shock). Reduce to 25-40% size or stand aside.",
            size_multiplier=0.30,
        )


# ---------------------------------------------------------------------------
# EIA Weekly Crude Inventory
# ---------------------------------------------------------------------------

def _next_wednesday() -> date:
    today = date.today()
    days_ahead = (2 - today.weekday()) % 7  # Wednesday = weekday 2
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _fetch_eia_inventory(api_key: Optional[str]) -> Optional[EIAInventoryReport]:
    """
    Fetch last 2 weeks of EIA crude oil stock data.
    Series: WCRSTUS1 — Weekly U.S. Ending Stocks of Crude Oil (thousand barrels).
    API: https://api.eia.gov/v2/petroleum/stoc/wstk/data/
    Falls back gracefully if no key is set.
    """
    import time as _time
    if _EIA_CACHE["ts"] and (_time.time() - _EIA_CACHE["ts"]) < _CACHE_TTL:
        return _EIA_CACHE["data"]

    if not api_key:
        logger.info("[EIA] No EIA_API_KEY set — inventory data unavailable")
        return None

    try:
        url = (
            "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
            f"?api_key={api_key}"
            "&frequency=weekly"
            "&data[0]=value"
            "&facets[series][]=WCRSTUS1"
            "&sort[0][column]=period"
            "&sort[0][direction]=desc"
            "&length=3"
        )
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        rows = resp.json().get("response", {}).get("data", [])
        if len(rows) < 2:
            logger.warning("[EIA] Not enough data rows returned")
            return None

        # rows[0] = most recent, rows[1] = prior week
        latest_val = float(rows[0]["value"])   # thousand barrels
        prior_val = float(rows[1]["value"])
        change_mbbl = round((latest_val - prior_val) / 1000, 2)  # → million barrels
        prior_change = round((prior_val - float(rows[2]["value"])) / 1000, 2) if len(rows) >= 3 else None
        report_date = rows[0]["period"]

        if change_mbbl < -1.0:
            direction = "bullish_draw"
            desc = f"Crude draw of {abs(change_mbbl):.1f}M bbl — bullish supply signal"
        elif change_mbbl > 1.0:
            direction = "bearish_build"
            desc = f"Crude build of {change_mbbl:.1f}M bbl — bearish supply signal"
        else:
            direction = "neutral"
            desc = f"Crude inventory change {change_mbbl:+.2f}M bbl — largely in-line"

        next_wed = _next_wednesday()
        result = EIAInventoryReport(
            report_date=report_date,
            change_mbbl=change_mbbl,
            prior_change_mbbl=prior_change,
            direction=direction,
            description=desc,
            next_report_date=next_wed.strftime("%Y-%m-%d"),
            days_to_next=(next_wed - date.today()).days,
        )
        _EIA_CACHE["ts"] = _time.time()
        _EIA_CACHE["data"] = result
        logger.info(f"[EIA] {report_date}: change={change_mbbl:+.2f}M bbl ({direction})")
        return result

    except Exception as e:
        logger.warning(f"[EIA] fetch failed: {e}")
        return None


# ---------------------------------------------------------------------------
# OPEC+ Calendar
# ---------------------------------------------------------------------------

def _check_opec_window() -> Optional[OpecWindow]:
    today = date.today()
    upcoming = sorted([m for m in _OPEC_MEETINGS if m >= today - timedelta(days=_OPEC_WINDOW_DAYS)])
    if not upcoming:
        return None

    next_meeting = upcoming[0]
    days_until = (next_meeting - today).days
    is_active = abs(days_until) <= _OPEC_WINDOW_DAYS

    if days_until < 0:
        msg = f"OPEC+ met {abs(days_until)}d ago — watch for delayed production decision leaks."
    elif days_until == 0:
        msg = "OPEC+ meeting TODAY — extreme caution, avoid intraday WTI positions."
    elif days_until <= _OPEC_WINDOW_DAYS:
        msg = f"OPEC+ meeting in {days_until}d — pre-meeting positioning risk. Reduce size."
    else:
        msg = f"Next OPEC+ meeting: {next_meeting.strftime('%d %b %Y')} ({days_until}d away)."

    return OpecWindow(
        next_meeting_date=next_meeting.strftime("%Y-%m-%d"),
        days_until=days_until,
        is_active_window=is_active,
        caution_message=msg,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def analyze_oil_market_context() -> OilMarketContext:
    """
    Build a complete OilMarketContext for WTI.
    Called once per WTI analysis cycle.
    """
    eia_api_key = os.environ.get("EIA_API_KEY")
    warnings: List[str] = []
    size_multipliers: List[float] = [1.0]

    # 1. OVX regime
    ovx_val = _fetch_ovx()
    ovx = _classify_ovx(ovx_val) if ovx_val is not None else None
    if ovx:
        size_multipliers.append(ovx.size_multiplier)
        if ovx.regime == "ELEVATED":
            warnings.append(f"OVX {ovx.current_value:.0f} — elevated oil volatility, reduce size to ~65%")
        elif ovx.regime == "EXTREME":
            warnings.append(f"OVX {ovx.current_value:.0f} — EXTREME volatility, consider standing aside")

    # 2. EIA inventory
    eia = _fetch_eia_inventory(eia_api_key)
    if eia:
        if eia.direction == "bearish_build":
            warnings.append(f"EIA: crude build {eia.change_mbbl:+.1f}M bbl — bearish supply pressure")
        elif eia.direction == "bullish_draw":
            warnings.append(f"EIA: crude draw {eia.change_mbbl:+.1f}M bbl — bullish supply signal")
        if eia.days_to_next is not None and eia.days_to_next <= 1:
            warnings.append("EIA crude inventory report due TOMORROW — high event risk")

    # 3. OPEC window
    opec = _check_opec_window()
    if opec and opec.is_active_window:
        warnings.append(opec.caution_message)
        size_multipliers.append(0.60)

    # Combine size guidance (take the most restrictive)
    size_guidance = round(min(size_multipliers), 2)

    # Overall regime
    if size_guidance <= 0.35 or (ovx and ovx.regime == "EXTREME"):
        overall_regime = "HIGH_RISK"
    elif size_guidance < 0.85 or len(warnings) >= 2:
        overall_regime = "CAUTION"
    else:
        overall_regime = "CLEAR"

    # Build summary
    parts = []
    if ovx:
        parts.append(f"OVX {ovx.current_value:.0f} ({ovx.regime_label})")
    if eia:
        parts.append(f"EIA: {eia.description}")
    if opec:
        parts.append(opec.caution_message)
    regime_summary = " | ".join(parts) if parts else "Oil market context unavailable"

    return OilMarketContext(
        ovx=ovx,
        eia_inventory=eia,
        opec_window=opec,
        overall_regime=overall_regime,
        regime_summary=regime_summary,
        size_guidance=size_guidance,
        warnings=warnings,
    )
