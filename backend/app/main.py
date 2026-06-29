from fastapi import FastAPI, HTTPException, Depends, Request
from starlette.middleware.sessions import SessionMiddleware
from mangum import Mangum
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor

# Import auth dependencies - these are light
from .auth import get_current_user
from .oauth import router as auth_router
from .news.geopolitical_routes import router as geopolitical_router
from .chat_routes import router as chat_router

# Base logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Primary DB abstraction
from . import db as nexus_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Market Analyzer API",
    description="Analyze instruments for trading opportunities",
    version="1.0.0"
)

# GLOBAL CACHE for expensive/slow benchmark data (10 min TTL)
# This prevents TwelveData 8-requests/min rate limits on refreshes
import time
_BENCHMARK_CACHE = {"timestamp": 0, "data": None}
_BENCH_TTL = 600

# GLOBAL CACHE for heavy history data (Monthly/Weekly) - 4 hour TTL
_HISTORY_CACHE = {} # { "SYMBOL_TIME": {"timestamp": 0, "df": df} }
_HISTORY_TTL = 14400


def _sane_entry(ideal_entry, current_price, max_dev_pct: float = 0.05):
    """Reject entry anchors that sit unrealistically far from the current price.

    Fibonacci swing levels computed over a long lookback (FIB_LOOKBACK_BARS) can
    land far from the live price (e.g. an old swing high). Anchoring stop/target
    there produces nonsensical levels (entry $99 when price is $71). If the
    candidate entry deviates more than ``max_dev_pct`` from current price, return
    None so the volatility analyzer falls back to anchoring on current price.
    """
    if ideal_entry is None or current_price is None or current_price <= 0:
        return None
    if abs(ideal_entry - current_price) / current_price > max_dev_pct:
        logger.info(
            f"[ENTRY] Rejecting ideal_entry={ideal_entry} (>{max_dev_pct:.0%} from "
            f"current_price={current_price}); anchoring to current price instead."
        )
        return None
    return ideal_entry


def _fetch_via_yfinance(ticker: str, days: int = 30):
    """Fetch daily OHLCV data via yfinance as a free alternative for DXY / US10Y.

    TwelveData free-tier consistently rejects DXY and TNX symbols.
    yfinance requires no API key and provides:
      - DXY  → US Dollar Index (spot index)
      - ^TNX  → CBOE 10-Year Treasury Yield (value = yield × 10, e.g. 42.5 = 4.25%)
    """
    try:
        import yfinance as yf  # lazy import — optional dependency
        import pandas as pd
        tkr = yf.Ticker(ticker)
        df = tkr.history(period=f"{days}d", interval="1d", auto_adjust=True)
        if df is None or df.empty:
            logger.warning(f"[YFINANCE] {ticker}: empty response")
            return None
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        result = df[cols].dropna()
        logger.info(f"[YFINANCE] {ticker}: {len(result)} daily bars fetched")
        return result
    except Exception as exc:
        logger.warning(f"[YFINANCE] {ticker} fetch failed: {exc}")
        return None 

# CORS Middleware
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:4200")
ALLOWED_ORIGINS = [
    "http://localhost:4200", 
    "http://127.0.0.1:4200", 
    FRONTEND_URL,
    "https://d3l5h8j5l8wq3.cloudfront.net"  # Current CloudFront URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Auth routes at top level - these are fast enough
app.include_router(auth_router, prefix="/api")
# Include Geopolitical routes
app.include_router(geopolitical_router)
# Include AI chat routes
app.include_router(chat_router)

# Required for Authlib OAuth state storage
SESSION_SECRET = os.environ.get("SESSION_SECRET", "super-secret-session-key")
app.add_middleware(
    SessionMiddleware, 
    secret_key=SESSION_SECRET,
    session_cookie="nexus_session",
    same_site="none",
    https_only=True
)

@app.get("/")
async def root():
    return {"message": "Market Analyzer API", "status": "running"}

@app.get("/api/health/config-check")
async def config_check():
    """Diagnostic endpoint to verify environment settings in production."""
    frontend_url = os.environ.get("FRONTEND_URL", "NOT_SET")
    env_name = os.environ.get("ENVIRONMENT", "NOT_SET")
    
    # Masking for security but revealing the domain
    masked_url = frontend_url if len(frontend_url) < 10 else f"{frontend_url[:15]}...{frontend_url[-10:]}"
    
    return {
        "environment": env_name,
        "frontend_url_detected": masked_url,
        "is_production": env_name == "production",
        "redirect_uri_config": os.environ.get("GOOGLE_REDIRECT_URI", "AUTO_RESOLVED"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Include Auth routes at top level - these are fast enough
app.include_router(auth_router, prefix="/api")

# Lazy analysis helper to keep imports deferred
def analyze_instrument_lazy(
    symbol: str, 
    name: str, 
    params: dict, 
    benchmark_direction: Any = None, 
    strategy_settings: Any = None, 
    mode: Any = None, 
    benchmark_data_df: Any = None,
    pre_macro_df: Any = None,
    pre_pullback_df: Any = None,
    pre_execution_df: Any = None,
    pre_expert_df: Any = None,
    pre_price: float = None,
    dxy_df: Any = None,
    us10y_df: Any = None,
    news_api_key: str = ''
) -> Any:
    """Perform complete analysis on a single instrument with lazy imports."""
    from .data_fetcher import fetch_historical_data, fetch_weekly_data, get_current_price
    from .analyzers import (
        analyze_monthly_trend, analyze_weekly_pullback, analyze_daily_strength,
        analyze_market_phase, analyze_volatility_and_risk, analyze_fundamentals,
        get_backtest_results, detect_candle_patterns, analyze_technical_indicators,
        analyze_news_sentiment, analyze_pullback_warning, analyze_relative_strength,
        analyze_intermarket_context, analyze_session_context,
        detect_opening_range, calculate_rvol, analyze_commodity_specifics, generate_expert_trade_plan,
        analyze_blowoff_top, analyze_position_exit, build_trade_plan,
    )
    from .signal_generator import generate_trade_signal
    from .models import InstrumentAnalysis, Signal, CandleAnalysis, PullbackWarningAnalysis, StrategyMode, IntermarketContext
    
    # Default to Long Term if not specified
    if mode is None:
        mode = StrategyMode.LONG_TERM
        
    logger.info(f"Analyzing {symbol} in {mode.value} mode...")
    
    if benchmark_direction is None:
        benchmark_direction = Signal.NEUTRAL
    
    # Timeframe selection based on mode - PERSISTENT CACHE OPTIMIZATION
    global _HISTORY_CACHE
    now = time.time()

    def get_cached_history(key, interval, days):
        cache_key = f"{key}_{interval}_{days}"
        if cache_key in _HISTORY_CACHE:
            entry = _HISTORY_CACHE[cache_key]
            if now - entry["timestamp"] < _HISTORY_TTL:
                return entry["df"]
        return None

    def set_cached_history(key, interval, days, df):
        if df is not None and not df.empty:
            cache_key = f"{key}_{interval}_{days}"
            _HISTORY_CACHE[cache_key] = {"timestamp": time.time(), "df": df}

    # 1. Macro Data (High latency, low change)
    if pre_macro_df is not None: macro_data = pre_macro_df
    else:
        macro_interval = "1month" if mode == StrategyMode.LONG_TERM else "1day"
        macro_days = 1000 if mode == StrategyMode.LONG_TERM else 500
        macro_data = get_cached_history(symbol, macro_interval, macro_days)
        if macro_data is None:
            logger.info(f"[FETCH] {symbol} macro ({macro_interval}, {macro_days}d) - cache miss, fetching...")
            macro_data = fetch_historical_data(symbol, days=macro_days, interval=macro_interval)
            set_cached_history(symbol, macro_interval, macro_days, macro_data)
            logger.info(f"[FETCH] {symbol} macro: {'OK' if macro_data is not None and not macro_data.empty else 'EMPTY'} ({len(macro_data) if macro_data is not None and not macro_data.empty else 0} bars)")
        else:
            logger.info(f"[FETCH] {symbol} macro: cache hit ({len(macro_data)} bars)")

    # 2. Pullback Data
    if pre_pullback_df is not None: pullback_data = pre_pullback_df
    else:
        pull_interval = "1week" if mode == StrategyMode.LONG_TERM else "4h"
        pull_days = 250 if mode == StrategyMode.LONG_TERM else 120
        pullback_data = get_cached_history(symbol, pull_interval, pull_days)
        if pullback_data is None:
            logger.info(f"[FETCH] {symbol} pullback ({pull_interval}, {pull_days}d) - cache miss, fetching...")
            pullback_data = fetch_historical_data(symbol, days=pull_days, interval=pull_interval)
            set_cached_history(symbol, pull_interval, pull_days, pullback_data)
            logger.info(f"[FETCH] {symbol} pullback: {'OK' if pullback_data is not None and not pullback_data.empty else 'EMPTY'} ({len(pullback_data) if pullback_data is not None and not pullback_data.empty else 0} bars)")
        else:
            logger.info(f"[FETCH] {symbol} pullback: cache hit ({len(pullback_data)} bars)")

    # 3. Execution Data (Low latency, high change - Always Fresh)
    if pre_execution_df is not None: execution_data = pre_execution_df
    else: execution_data = fetch_historical_data(symbol, days=(500 if mode == StrategyMode.LONG_TERM else 300), interval=("1day" if mode == StrategyMode.LONG_TERM else "1h"))

    if mode == StrategyMode.LONG_TERM:
        macro_label = "Institutional (Long-Term)"
        pullback_label = "Swing Portfolio"
        execution_label = "Tactical Entry"
    else:
        macro_label = "Institutional (Short-Term)"
        pullback_label = "Day Trading"
        execution_label = "Execution (H1)"

    # Price Strategy:
    # - pre_price: live price pre-fetched in batch by the scan endpoint (1 API call for all instruments).
    # - Fallback: last candle close (hourly in SHORT_TERM = fresh enough; daily in LONG_TERM = may lag by hours).
    candle_price = float(execution_data['Close'].iloc[-1]) if not execution_data.empty else None
    if pre_price and pre_price > 0:
        current_price = pre_price
        logger.info(f"Using pre-fetched live price for {symbol}: {current_price}")
    elif candle_price is not None:
        current_price = candle_price
        logger.info(f"Using latest candle price for {symbol}: {current_price}")
    else:
        raise ValueError(f"No price available for {symbol}")
    
    trend = analyze_monthly_trend(macro_data, params.get('monthly', {}))
    # Update description to reflect timeframe
    trend.description = f"[{macro_label}] " + trend.description
    
    pullback = analyze_weekly_pullback(pullback_data, current_price, params.get('weekly', {}))
    pullback.description = f"[{pullback_label}] " + pullback.description
    
    strength = analyze_daily_strength(execution_data, params.get('daily', {}))
    # Override price change to be TRUE DAILY change.
    # LONG_TERM: execution_data is already 1d.
    # SHORT_TERM: prefer macro_data (1d), and fall back to a fresh 1d fetch if missing.
    daily_source = execution_data if mode == StrategyMode.LONG_TERM else macro_data
    if daily_source is None or daily_source.empty or len(daily_source) < 2:
        try:
            daily_source = fetch_historical_data(symbol, days=10, interval="1day")
        except Exception as _e:
            logger.warning(f"Failed to fetch fallback daily source for {symbol}: {_e}")
            daily_source = None

    if daily_source is not None and not daily_source.empty and len(daily_source) >= 2:
        daily_change = float(((daily_source['Close'].iloc[-1] - daily_source['Close'].iloc[-2]) / daily_source['Close'].iloc[-2]) * 100)
        strength.price_change_percent = float(round(daily_change, 2))
    strength.description = f"[{execution_label}] " + strength.description
    
    phase = analyze_market_phase(execution_data, params.get('daily', {}))
    candle_data = detect_candle_patterns(execution_data)
    
    candle_model = CandleAnalysis(
        pattern=candle_data['pattern'],
        description=candle_data['description'],
        is_bullish=candle_data.get('is_bullish')
    )
    
    tech_indicators = analyze_technical_indicators(execution_data)
    news_sentiment = analyze_news_sentiment(symbol, api_key=news_api_key)
    session_ctx = analyze_session_context(execution_data)

    # NEW: Expert Day Trader Logic (15m/short-term specific)
    # Pre-compute inputs here; actual plan is built after trade_signal so it uses the final recommendation.
    expert_plan = None
    _expert_or_data = None
    _expert_rvol = 1.0
    _expert_advice = ""
    if mode == StrategyMode.SHORT_TERM and pre_expert_df is not None and not pre_expert_df.empty:
        _expert_or_data = detect_opening_range(pre_expert_df)
        _expert_rvol = calculate_rvol(pre_expert_df)
        dxy_chg = 0.0
        yield_chg = 0.0
        if dxy_df is not None and len(dxy_df) >= 2:
            dxy_chg = float((dxy_df['Close'].iloc[-1] - dxy_df['Close'].iloc[-2]) / dxy_df['Close'].iloc[-2] * 100)
        if us10y_df is not None and len(us10y_df) >= 2:
            yield_chg = float((us10y_df['Close'].iloc[-1] - us10y_df['Close'].iloc[-2]) / us10y_df['Close'].iloc[-2] * 100)
        _expert_advice = analyze_commodity_specifics(symbol, dxy_chg, yield_chg)
    
    # NEW: Intermarket Context (DXY / Yields)
    intermarket = analyze_intermarket_context(symbol, dxy_df, us10y_df)

    # Derive ideal entry price for pending setups so stop/target anchor to entry zone.
    # Frontend shows S1/Fib entry zone for any non-bearish signal (isBullish = rec != 'bearish'),
    # so neutral must also anchor to S1/Fib — not to current price.
    ideal_entry = None
    if tech_indicators and tech_indicators.pivot_points and tech_indicators.fibonacci:
        pp = tech_indicators.pivot_points
        fib = tech_indicators.fibonacci
        if trend.direction.value == "bearish" and pp.r1 and fib.ret_618:
            ideal_entry = max(pp.r1, fib.ret_618)
        elif pp.s1 and fib.ret_382:
            ideal_entry = min(pp.s1, fib.ret_382)
        # Guard against far-away swing levels producing unreachable entries.
        ideal_entry = _sane_entry(ideal_entry, current_price)

    # Initial volatility calculation using trend direction (may be updated after trade signal)
    volatility = analyze_volatility_and_risk(execution_data, current_price, trend.direction.value, entry_price=ideal_entry)
    fundamentals = analyze_fundamentals(symbol)
    blowoff_top = analyze_blowoff_top(
        symbol=symbol,
        df=execution_data,
        technical_indicators=tech_indicators,
        volatility=volatility,
    )
    
    # NEW: Relative Strength Analysis (Alpha vs Beta)
    # Commodities (WTI/XAU/XAG) → compare against DXY (DXY falls = gold/oil outperforms).
    # Crypto → compare against BTC.  Everything else → SPX.
    _COMMODITY_SYMS_RS = {"WTI", "XAU", "XAG", "GOLD", "SILVER", "OIL"}
    _is_crypto_rs  = any(sub in symbol.upper() for sub in ["BTC", "ETH", "CRYPTO", "BITCOIN"]) or (len(symbol) > 6 and "USD" in symbol.upper())
    _is_commodity_rs = any(sub in symbol.upper() for sub in _COMMODITY_SYMS_RS)

    if _is_commodity_rs:
        bench_sym = "DXY"
        # Use the already-fetched 60-day DXY dataframe; fall back to a live fetch if missing.
        if dxy_df is not None and not dxy_df.empty:
            bench_data = dxy_df
        else:
            bench_data = _fetch_via_yfinance("DX-Y.NYB", 60)
    elif _is_crypto_rs:
        bench_sym = "BTC"
        bench_data = benchmark_data_df if benchmark_data_df is not None else fetch_historical_data(
            bench_sym, days=(500 if mode == StrategyMode.LONG_TERM else 20),
            interval=("1day" if mode == StrategyMode.LONG_TERM else "1h")
        )
    else:
        bench_sym = "SPX"
        bench_data = benchmark_data_df if benchmark_data_df is not None else fetch_historical_data(
            bench_sym, days=(500 if mode == StrategyMode.LONG_TERM else 20),
            interval=("1day" if mode == StrategyMode.LONG_TERM else "1h")
        )
    
    rs_analysis = analyze_relative_strength(
        execution_data,
        bench_data,
        symbol,
        bench_sym,
        lookback_periods=20
    )
    
    # Pullback warning is part of score context and must be included before
    # final recommendation/action classification.
    pullback_warning = analyze_pullback_warning(execution_data, trend.direction)

    trade_signal = generate_trade_signal(
        trend=trend, 
        pullback=pullback, 
        strength=strength, 
        candle=candle_model, 
        benchmark_direction=benchmark_direction,
        settings=strategy_settings,
        current_price=current_price,
        tech_indicators=tech_indicators,
        volatility=volatility,
        fundamentals=fundamentals,
        relative_strength=rs_analysis,
        blowoff_top=blowoff_top,
        strategy_mode=mode.value,
        pullback_warning=pullback_warning,
        news_sentiment_label=news_sentiment.label,
        benchmark_symbol=bench_sym,
    )

    # Recalculate volatility using the actual trade signal recommendation
    # to ensure stop/target values match the trade direction
    ideal_entry_for_signal = None
    if tech_indicators and tech_indicators.pivot_points and tech_indicators.fibonacci:
        pp = tech_indicators.pivot_points
        fib = tech_indicators.fibonacci
        if trade_signal.recommendation.value == "bearish" and pp.r1 and fib.ret_618:
            ideal_entry_for_signal = max(pp.r1, fib.ret_618)
        elif pp.s1 and fib.ret_382:
            ideal_entry_for_signal = min(pp.s1, fib.ret_382)
        # Guard against far-away swing levels producing unreachable entries.
        ideal_entry_for_signal = _sane_entry(ideal_entry_for_signal, current_price)
    
    logger.info(f"[{symbol}] Volatility recalc: recommendation={trade_signal.recommendation.value}, ideal_entry={ideal_entry_for_signal}, current_price={current_price}")
    volatility = analyze_volatility_and_risk(execution_data, current_price, trade_signal.recommendation.value, entry_price=ideal_entry_for_signal)
    logger.info(f"[{symbol}] Volatility result: anchor={volatility.entry_price}, sl={volatility.stop_loss}, tp={volatility.take_profit}")

    # ── Canonical trade plan — SINGLE SOURCE OF TRUTH for entry/stop/targets ──
    # Built once from the FINAL volatility levels + structural context. Every UI
    # surface (level card, Strategic Action, Battle Plan, scaling) renders from
    # this so the numbers can never diverge.
    trade_plan = build_trade_plan(
        signal_direction=trade_signal.recommendation.value,
        current_price=current_price,
        volatility=volatility,
        tech_indicators=tech_indicators,
        is_actionable=trade_signal.trade_worthy,
        or_data=_expert_or_data,
    )

    # Keep the Strategic Action scaling narrative numerically in sync with the
    # final plan (it was generated earlier off the pre-recalc volatility).
    if trade_plan and trade_plan.direction != "neutral":
        trade_signal.scaling_plan = (
            f"Stage 1 (De-risk): Exit 30% at ${trade_plan.take_profit_1:.2f} & move stop to break-even. "
            f"Stage 2 (Profit): Exit 40% at ${trade_plan.take_profit_2:.2f}. "
            f"Stage 3 (Runner): Leave 30% for ${trade_plan.take_profit_3:.2f} or trail by 2.0x ATR."
        )

    # Build expert plan now that trade_signal.recommendation is final and the
    # canonical trade plan is available (numbers come from the plan).
    if _expert_or_data is not None:
        expert_plan = generate_expert_trade_plan(
            symbol, current_price, _expert_or_data, _expert_rvol, tech_indicators, _expert_advice,
            signal_direction=trade_signal.recommendation.value,
            atr=float(volatility.atr),
            rsi=float(strength.rsi),
            adx=float(strength.adx),
            session_ctx=session_ctx,
            trade_plan=trade_plan,
        )

    # Selection of daily data for backtesting (1Y perspective)
    backtest_source = execution_data if mode == StrategyMode.LONG_TERM else macro_data
    backtest = get_backtest_results(symbol, backtest_source, params, settings=strategy_settings)

    # P6: Volume Profile (50-bucket LT, 20-bucket ST)
    from .analyzers.volume_profile_analyzer import calculate_volume_profile
    volume_profile = calculate_volume_profile(execution_data, mode=mode)

    # P7: Session VWAP (intraday data — use expert_df 15min or exec hourly)
    from .analyzers.session_vwap_analyzer import calculate_session_vwap
    vwap_source = pre_expert_df if pre_expert_df is not None and len(pre_expert_df) > 5 else pre_execution_df
    session_vwap = calculate_session_vwap(vwap_source, current_price)

    # P8: Liquidity Map (top 3 per side)
    from .analyzers.liquidity_map_analyzer import calculate_liquidity_map
    liquidity_map = calculate_liquidity_map(execution_data, current_price)

    # P9: Block Flow Detector
    from .analyzers.block_flow_analyzer import detect_block_flow
    block_flow = detect_block_flow(execution_data, current_price)

    # P10: Geopolitical Risk — cross-validate news keywords with indicators
    from .analyzers.geo_risk_analyzer import analyze_geopolitical_risk
    geopolitical_risk = analyze_geopolitical_risk(
        symbol=symbol,
        news_sentiment=news_sentiment,
        strength=strength,
        volatility=volatility,
        trade_signal=trade_signal,
    )

    # P11: Position Exit Analysis - systematic loss-cutting mechanism
    # This detects when short-term trends contradict long-term positions.
    # Align the assumed position side with the system's actual directional view
    # (trend first, then the composite recommendation) so the exit alert never
    # contradicts the displayed bias. If neither is directional, leave it None
    # and the analyzer reports "not applicable" instead of guessing a side.
    exit_side = None
    if trend.direction == Signal.BULLISH:
        exit_side = "long"
    elif trend.direction == Signal.BEARISH:
        exit_side = "short"
    elif trade_signal.recommendation == Signal.BULLISH:
        exit_side = "long"
    elif trade_signal.recommendation == Signal.BEARISH:
        exit_side = "short"

    position_exit = analyze_position_exit(
        trend=trend,
        strength=strength,
        volatility=volatility,
        technical_indicators=tech_indicators,
        current_price=current_price,
        assumed_position_side=exit_side,
        execution_data=execution_data,
        trade_plan=trade_plan,
    )

    # P12: Intraday Signals (for INTRADAY mode)
    intraday_signals = None
    if mode == StrategyMode.INTRADAY:
        from .analyzers.intraday_signal_generator import detect_intraday_signals_verbose
        # Fetch intraday timeframes: 4H, 1H, 15m
        bars_4h = fetch_historical_data(symbol, days=30, interval="4h")
        bars_1h = fetch_historical_data(symbol, days=14, interval="1h")
        bars_15m = fetch_historical_data(symbol, days=3, interval="15m")
        intraday_signals, _ = detect_intraday_signals_verbose(
            symbol=symbol,
            name=name,
            bars_4h=bars_4h,
            bars_1h=bars_1h,
            bars_15m=bars_15m,
        )

    return InstrumentAnalysis(
        symbol=symbol,
        name=name,
        current_price=round(current_price, 2),
        analysis_date=date.today(),
        last_updated=datetime.now(timezone.utc).isoformat(),
        monthly_trend=trend,
        weekly_pullback=pullback,
        daily_strength=strength,
        market_phase=phase,
        volatility_risk=volatility,
        fundamentals=fundamentals,
        backtest_results=backtest,
        candle_patterns=candle_model,
        intraday_signals=intraday_signals,
        benchmark_direction=benchmark_direction,
        trade_signal=trade_signal,
        technical_indicators=tech_indicators,
        news_sentiment=news_sentiment,
        relative_strength=rs_analysis,
        expert_trade_plan=expert_plan,
        strategy_mode=mode,
        intermarket_context=intermarket,
        session_context=session_ctx,
        volume_profile=volume_profile,
        session_vwap=session_vwap,
        liquidity_map=liquidity_map,
        block_flow=block_flow,
        geopolitical_risk=geopolitical_risk,
        blowoff_top=blowoff_top,
        position_exit=position_exit,
        trade_plan=trade_plan,
    ), execution_data

# In-memory store for sent alerts
SENT_ALERTS = set()


def is_weekend_market_close() -> bool:
    """Return True during the commodity/forex weekend-close window.

    WTI, XAU, XAG markets close Friday ~22:00 UTC and reopen Sunday ~21:00 UTC.
    BTC is 24/7 but weekend analysis adds little signal value.
    Returning True suppresses alerts during this window; cache still serves the UI.
    """
    now = datetime.now(timezone.utc)
    wd  = now.weekday()          # 5 = Saturday, 6 = Sunday, 0-4 = Mon-Fri
    if wd == 5:                  # All day Saturday
        return True
    if wd == 4 and now.hour >= 22:  # Friday after 22:00 UTC (5pm ET)
        return True
    if wd == 6 and now.hour < 21:   # Sunday before 21:00 UTC (markets still closed)
        return True
    return False

async def run_scheduled_analysis(user_id: str = "global_default", mode: Any = None):
    from .config_loader import load_config, get_instruments, get_analysis_params, get_alert_config, get_strategy_config, get_newsapi_key
    from .models import StrategySettings, Signal, StrategyMode
    from .data_fetcher import fetch_historical_data
    from .analyzers import (
        analyze_monthly_trend, calculate_weekly_performance, 
        calculate_correlations, apply_position_sizing, analyze_psychological_state
    )
    from .notifier import send_alerts, send_expert_alert
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    if mode is None:
        mode = StrategyMode.LONG_TERM

    # Scheduler skip if no active user
    if user_id == "global_default":
        # Check if we have a shared cache first to avoid re-calculating for every scheduler trigger
        if nexus_db.is_dynamo_enabled():
            cached = nexus_db.get_latest_analysis_results(user_id, mode.value, max_age_seconds=240)
            if cached:
                logger.info(f"System scheduler: Serving cached results for {user_id}")
                return cached.get('instruments', []), cached.get('weekly_performance', {}), cached.get('correlation_data', {}), cached.get('psychological_guardrail', {})
        
        logger.info(f"System scheduler: Running fresh analysis for {user_id}...")
    
    # 1. Check Cache First
    if nexus_db.is_dynamo_enabled():
        cached = nexus_db.get_latest_analysis_results(user_id, mode.value, max_age_seconds=240) # 4 min cache
        if cached:
            logger.info(f"Serving cached results for {user_id} ({mode.value})")
            from .models import InstrumentAnalysis, PerformanceSummary, CorrelationData, PsychologicalGuardrail
            # Reconstruct models from dict
            try:
                results = [InstrumentAnalysis(**i) for i in cached.get('instruments', [])]
                perf = PerformanceSummary(**cached.get('weekly_performance', {}))
                corr = CorrelationData(**cached.get('correlation_data', {}))
                # guardrail might be missing in old cache
                guard_dict = cached.get('psychological_guardrail')
                guard = PsychologicalGuardrail(**guard_dict) if guard_dict else None
                return results, perf, corr, guard
            except Exception as e:
                logger.warning(f"Failed to reconstruct models from cache: {e}")
                # Fall back to fresh analysis

    t_scan_start = time.time()
    logger.info(f"[SCAN_START] user={user_id} mode={mode.value} timestamp={datetime.now(timezone.utc).isoformat()}")
    config = load_config(user_id=user_id)
    instruments = get_instruments(config)
    logger.info(f"Loaded {len(instruments)} instruments for user {user_id}")
    
    params = get_analysis_params(config)
    alert_config = get_alert_config(config)
    newsapi_key = get_newsapi_key(config)
    
    try:
        strategy_settings = StrategySettings(**get_strategy_config(config))
    except Exception as e:
        logger.error(f"Failed to parse strategy settings: {e}. Using defaults.")
        strategy_settings = StrategySettings(**{
            "conviction_threshold": 70,
            "adx_threshold": 25,
            "atr_multiplier_tp": 3.0,
            "atr_multiplier_sl": 1.5,
            "portfolio_value": 10000.0,
            "risk_per_trade_percent": 1.0,
            "aggressiveness_mode": "balanced",
        })
    
    # Performance Context: Intervals for scan
    from .models import StrategyMode
    bench_interval = "1month" if mode == StrategyMode.LONG_TERM else "1day"
    exec_interval = "1day" if mode == StrategyMode.LONG_TERM else "1h"
    exec_days = 500 if mode == StrategyMode.LONG_TERM else 20

    # 4. Optimized Benchmarks: Fetch once and share (BATCHED)
    global _BENCHMARK_CACHE
    now = time.time()
    
    if now - _BENCHMARK_CACHE["timestamp"] < _BENCH_TTL and _BENCHMARK_CACHE["data"] is not None:
        cache_age = round(now - _BENCHMARK_CACHE["timestamp"], 0)
        logger.info(f"[BENCHMARKS] Cache hit (age={cache_age}s, TTL={_BENCH_TTL}s)")
        benchmarks_data = _BENCHMARK_CACHE["data"]
    else:
        logger.info(f"[BENCHMARKS] Cache miss or expired — fetching fresh via BATCH (bench={bench_interval}, exec={exec_interval})")
        from .twelvedata_fetcher import TwelveDataFetcher
        shared_fetcher = TwelveDataFetcher()
        # Fetch SPX/BTC in their own batch — isolate DXY/TNX so a DXY failure
        # cannot contaminate the SPX/BTC chunk (DXY is invalid on some API plans)
        core_bench = ["SPX", "BTC"]
        b_macro = shared_fetcher.fetch_batch_data(core_bench, interval=bench_interval, days=1000)
        b_exec  = shared_fetcher.fetch_batch_data(core_bench, interval=exec_interval, days=exec_days)

        # DXY / TNX are fetched via yfinance (free, no API key) in parallel with
        # the TwelveData batch above.  If yfinance is unavailable or returns empty
        # data, intermarket analysis degrades gracefully to None.
        with ThreadPoolExecutor(max_workers=2) as _yfin_pool:
            _f_dxy   = _yfin_pool.submit(_fetch_via_yfinance, "DX-Y.NYB",  60)
            _f_us10y = _yfin_pool.submit(_fetch_via_yfinance, "^TNX",  60)
            _dxy_df   = _f_dxy.result()
            _us10y_df = _f_us10y.result()

        benchmarks_data = {
            "SPX_macro": b_macro.get("SPX"),
            "BTC_macro": b_macro.get("BTC"),
            "SPX_exec": b_exec.get("SPX"),
            "BTC_exec": b_exec.get("BTC"),
            "DXY": _dxy_df,
            "US10Y": _us10y_df,
        }
        bench_summary = {k: ('OK' if v is not None and not v.empty else 'MISSING') for k, v in benchmarks_data.items()}
        logger.info(f"[BENCHMARKS] Fetch result: {bench_summary}")
        _BENCHMARK_CACHE = {"timestamp": now, "data": benchmarks_data}

    spy_bench = Signal.NEUTRAL
    btc_bench = Signal.NEUTRAL
    if benchmarks_data.get("SPX_macro") is not None and not benchmarks_data["SPX_macro"].empty:
        spy_bench = analyze_monthly_trend(benchmarks_data["SPX_macro"], params.get('monthly', {})).direction
    if benchmarks_data.get("BTC_macro") is not None and not benchmarks_data["BTC_macro"].empty:
        btc_bench = analyze_monthly_trend(benchmarks_data["BTC_macro"], params.get('monthly', {})).direction

    # Commodity benchmark: use inverted DXY (weak dollar = bullish for WTI/XAU/XAG)
    # DXY direction is derived from a 20-bar MA comparison on the 60-day daily data.
    commodity_bench = Signal.NEUTRAL
    _dxy_data = benchmarks_data.get("DXY")
    if _dxy_data is not None and not _dxy_data.empty and len(_dxy_data) >= 20:
        _dxy_close = _dxy_data['Close']
        _dxy_ma = _dxy_close.rolling(20).mean().iloc[-1]
        _dxy_cur = _dxy_close.iloc[-1]
        if _dxy_cur > _dxy_ma * 1.005:    # Dollar strong → headwind for commodities
            commodity_bench = Signal.BEARISH
        elif _dxy_cur < _dxy_ma * 0.995:  # Dollar weak  → tailwind for commodities
            commodity_bench = Signal.BULLISH
        # else stays NEUTRAL (no beta filter applied)
    logger.info(f"[BENCHMARKS] spy={spy_bench.value}, btc={btc_bench.value}, commodity(DXY-inv)={commodity_bench.value}")
            
    # 5. TIERED BATCH FETCH (The "Speed & Limit" Solution)
    # We only fetch LIVE data (Execution/Expert) on refresh. 
    # Macro/Pullback are cached for 4 hours in analyze_instrument_lazy because they change slowly.
    # Note: Use the ALREADY DEFINED shared_fetcher or create if benchmarking was skipped
    if 'shared_fetcher' not in locals():
        from .twelvedata_fetcher import TwelveDataFetcher
        shared_fetcher = TwelveDataFetcher()
        
    sym_list = [inst['symbol'] for inst in instruments]
    exec_fetch_interval = "1day" if mode == StrategyMode.LONG_TERM else "1h"
    logger.info(f"[INSTRUMENTS] Fetching execution data for {sym_list} @ {exec_fetch_interval}")
    
    with ThreadPoolExecutor(max_workers=2) as batch_executor: # Reduced workers to 2 to prevent rate-limit "bursts"
        # Always fetch Live Execution data (Daily/Hourly)
        f_exec = batch_executor.submit(
            shared_fetcher.fetch_batch_data, 
            sym_list, 
            interval=exec_fetch_interval, 
            days=500 if mode == StrategyMode.LONG_TERM else 60  # SHORT_TERM: 60d×24h=1440 bars, enough for all indicators
        )
        
        # Optional: Expert 15-minute data
        f_expert = None
        if mode == StrategyMode.SHORT_TERM:
            f_expert = batch_executor.submit(
                shared_fetcher.fetch_batch_data,
                sym_list,
                interval="15min",
                days=10
            )

        # STUB: Macro/Pullback will return EMPTY if not cached, and analyzer will use previous 
        # (Alternatively, we can fetch them only if Cache is empty)
        exec_batch = f_exec.result()
        expert_batch = f_expert.result() if f_expert else {}
        logger.info(f"[INSTRUMENTS] Exec batch fetched: {list(exec_batch.keys())} (missing: {[s for s in sym_list if s not in exec_batch]})")
        if expert_batch:
            logger.info(f"[INSTRUMENTS] Expert 15min batch: {list(expert_batch.keys())}")

        # Fetch live prices for all instruments in ONE API call for BOTH modes.
        # This keeps displayed current_price consistent between short_term and long_term views.
        live_prices = shared_fetcher.fetch_batch_prices(sym_list)

        # We'll allow the analyzer to use whatever history it has from previous runs or fall back
        macro_batch = {}
        pullback_batch = {}

    results = []
    data_map = {}

    def process_instrument(inst):
        sym = inst['symbol'].upper()
        t_inst = time.time()
        try:
            # Benchmark assignment: crypto→BTC, commodity→inverted-DXY, equity→SPX
            _COMMODITY_SYMS = {"WTI", "XAU", "XAG", "GOLD", "SILVER", "OIL"}
            is_crypto = any(sub in sym for sub in ["BTC", "CRYPTO", "BITCOIN"]) or (len(sym) > 6 and "USD" in sym)
            is_commodity = any(sub in sym for sub in _COMMODITY_SYMS)
            if is_crypto:
                bench = btc_bench
                bench_exec_df = benchmarks_data.get("BTC_exec")
            elif is_commodity:
                bench = commodity_bench  # inverted DXY — correct driver for WTI/XAU/XAG
                bench_exec_df = None     # no exec-level benchmark needed for commodities
            else:
                bench = spy_bench
                bench_exec_df = benchmarks_data.get("SPX_exec")
            
            # Pass pre-fetched data
            analysis, hist_data = analyze_instrument_lazy(
                sym, inst['name'], params, bench, strategy_settings, mode=mode, 
                benchmark_data_df=bench_exec_df,
                pre_macro_df=macro_batch.get(sym),
                pre_pullback_df=pullback_batch.get(sym),
                pre_execution_df=exec_batch.get(sym),
                pre_expert_df=expert_batch.get(sym),
                pre_price=live_prices.get(sym),
                dxy_df=benchmarks_data.get("DXY"),
                us10y_df=benchmarks_data.get("US10Y"),
                news_api_key=newsapi_key
            )
            # Oil market context — only for WTI
            if is_commodity and "WTI" in sym and analysis:
                try:
                    from .analyzers.oil_market_analyzer import analyze_oil_market_context
                    analysis.oil_market_context = analyze_oil_market_context()
                    logger.info(f"[OIL_CTX] {sym}: regime={analysis.oil_market_context.overall_regime}, size_guidance={analysis.oil_market_context.size_guidance}")
                except Exception as oil_exc:
                    logger.warning(f"[OIL_CTX] {sym}: failed to build oil context: {oil_exc}")

            elapsed_inst = round(time.time() - t_inst, 2)
            signal_rec = analysis.trade_signal.recommendation if analysis and analysis.trade_signal else 'N/A'
            price = analysis.current_price if analysis else 'N/A'
            logger.info(f"[ANALYSIS] {sym}: price={price}, signal={signal_rec}, elapsed={elapsed_inst}s")
            return sym, analysis, hist_data
        except Exception as e:
            logger.error(f"[ANALYSIS] {sym} FAILED after {round(time.time()-t_inst,2)}s: {e}")
            return sym, None, None

    # Parallelize analysis only (data is already fetched)
    try:
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_inst = {executor.submit(process_instrument, inst): inst for inst in instruments}
            for future in as_completed(future_to_inst):
                # Isolate each instrument so a single failure (including a fallback
                # construction error) can NEVER abort the whole scan and empty the list.
                inst_cfg = future_to_inst[future]
                try:
                    sym, analysis, hist_data = future.result()
                except Exception as inst_exc:
                    sym = (inst_cfg.get('symbol') if isinstance(inst_cfg, dict) else None) or 'UNKNOWN'
                    logger.error(f"Instrument task failed for {sym}: {inst_exc}", exc_info=True)
                    sym, analysis, hist_data = sym, None, None

                if analysis:
                    results.append(analysis)
                    data_map[sym] = hist_data
                    # Alerts — suppressed during weekend commodity/forex close
                    if not is_weekend_market_close():
                        if analysis.trade_signal.trade_worthy:
                            alert_key = f"{user_id}_{sym}_{analysis.trade_signal.recommendation}_{date.today()}_{mode.value}"
                            if alert_key not in SENT_ALERTS:
                                send_alerts(analysis, alert_config)
                                SENT_ALERTS.add(alert_key)
                        # Expert Battle Plan alert: only for actual ORB breaks (or_broken != 'none')
                        # with high intent — send_expert_alert also guards internally, but we skip
                        # adding noise keys to SENT_ALERTS for consolidating states.
                        if analysis.expert_trade_plan:
                            or_broken = analysis.expert_trade_plan.get('or_broken', 'none')
                            is_high_intent = analysis.expert_trade_plan.get('is_high_intent', False)
                            if or_broken != 'none' and is_high_intent:
                                expert_key = f"expert_{user_id}_{sym}_{or_broken}_{date.today()}_{mode.value}"
                                if expert_key not in SENT_ALERTS:
                                    send_expert_alert(analysis, alert_config)
                                    SENT_ALERTS.add(expert_key)
                else:
                    logger.warning(f"Analysis produced no result for {sym}")
    except Exception as e:
        logger.error(f"Parallel analysis loop failed: {e}", exc_info=True)
        # Continue with whatever results we have (possibly empty)

    perf_summary = calculate_weekly_performance(instruments, data_map, params, {"SPX": spy_bench, "BTC": btc_bench}, strategy_settings)

    # Build combined data map including benchmarks for correlation
    full_data_map = dict(data_map)
    if benchmarks_data.get("DXY") is not None and not benchmarks_data["DXY"].empty:
        full_data_map["DXY"] = benchmarks_data["DXY"]
    if benchmarks_data.get("SPX_macro") is not None and not benchmarks_data["SPX_macro"].empty:
        full_data_map["SPX"] = benchmarks_data["SPX_macro"]
    if benchmarks_data.get("BTC_macro") is not None and not benchmarks_data["BTC_macro"].empty:
        full_data_map["BTC"] = benchmarks_data["BTC_macro"]

    correlation_results = calculate_correlations(full_data_map)
    results = _attach_instrument_correlations(results, correlation_results)
    results = apply_position_sizing(results, correlation_results, strategy_settings)
    
    # NEW: Psychological Guardrail (Lockdown Logic)
    # Default limits: -2% Max Loss, 3 Losing Streak
    guardrail = analyze_psychological_state(
        perf_summary, 
        daily_loss_limit=-2.5 if mode == StrategyMode.LONG_TERM else -1.5,
        max_losing_streak=3
    )

    total_elapsed = round(time.time() - t_scan_start, 2)
    logger.info(f"[SCAN_COMPLETE] user={user_id} mode={mode.value} instruments={[a.symbol for a in results]} guardrail={guardrail.status} total_elapsed={total_elapsed}s")
    return results, perf_summary, correlation_results, guardrail

import math


def _attach_instrument_correlations(results, correlation_results):
    """Extract per-instrument correlation vs DXY, SPX, BTC from full matrix and attach to each analysis."""
    from .models import InstrumentCorrelations
    labels = correlation_results.get('labels', [])
    matrix = correlation_results.get('matrix', [])
    if not labels or not matrix:
        return results

    BENCHMARK_KEYS = {'DXY': 'vs_dxy', 'SPX': 'vs_spx', 'BTC': 'vs_btc'}

    updated = []
    for analysis in results:
        sym = analysis.symbol.upper()
        if sym not in labels:
            updated.append(analysis)
            continue
        s_idx = labels.index(sym)
        corr_vals = {}
        for bench, field in BENCHMARK_KEYS.items():
            if bench in labels:
                b_idx = labels.index(bench)
                corr_vals[field] = round(float(matrix[s_idx][b_idx]), 2)

        # Build interpretation
        dxy_corr = corr_vals.get('vs_dxy')
        spx_corr = corr_vals.get('vs_spx')
        parts = []
        if dxy_corr is not None:
            lbl = "strong negative" if dxy_corr < -0.6 else "negative" if dxy_corr < -0.3 else "positive" if dxy_corr > 0.3 else "neutral"
            parts.append(f"{lbl} DXY correlation ({dxy_corr:+.2f})")
        if spx_corr is not None:
            lbl = "strong positive" if spx_corr > 0.6 else "positive" if spx_corr > 0.3 else "negative" if spx_corr < -0.3 else "neutral"
            parts.append(f"{lbl} SPX correlation ({spx_corr:+.2f})")
        interpretation = "; ".join(parts) if parts else "Insufficient correlation data"

        inst_corr = InstrumentCorrelations(
            vs_dxy=corr_vals.get('vs_dxy'),
            vs_spx=corr_vals.get('vs_spx'),
            vs_btc=corr_vals.get('vs_btc'),
            period_days=30,
            interpretation=interpretation
        )
        updated.append(analysis.model_copy(update={"instrument_correlations": inst_corr}))
    return updated


def _scrub_nans(obj):
    """Recursively replaces NaN and Infinity with 0.0 to prevent Starlette JSON crashes."""
    if isinstance(obj, dict):
        return {k: _scrub_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_scrub_nans(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
    return obj

@app.get("/api/analyze")
async def analyze_all(mode: Any = None, refresh: bool = False, user_id: str = Depends(get_current_user)):
    from .models import AnalysisResponse, StrategyMode
    
    # Cast mode if string
    if isinstance(mode, str):
        try:
            mode = StrategyMode(mode)
        except ValueError:
            mode = StrategyMode.LONG_TERM
    if mode is None:
        mode = StrategyMode.LONG_TERM
    
    def _cache_age_minutes(cached: dict) -> int:
        """Calculate how many minutes old a cached result is."""
        try:
            ts = cached.get("analysis_timestamp", "")
            if ts:
                from datetime import datetime, timezone
                cached_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                delta = datetime.now(timezone.utc) - cached_dt
                return max(0, int(delta.total_seconds() / 60))
        except Exception:
            pass
        return 0

    # 1. Optimistic Cache check (if not forced refresh)
    # If we have something in cache less than 5 minutes old, serve it fast.
    if not refresh and nexus_db.is_dynamo_enabled():
        cached = nexus_db.get_latest_analysis_results(user_id, mode.value, max_age_seconds=300)
        if cached:
            age_min = _cache_age_minutes(cached)
            logger.info(f"Fast-path: Serving cached {mode.value} for {user_id} (age={age_min}m)")
            resp = AnalysisResponse(**cached)
            resp.served_from_cache = True
            resp.data_age_minutes = age_min
            return _scrub_nans(resp.dict())
    
    # 2. Perform Fresh Analysis
    try:
        results, perf, corr, guardrail = await run_scheduled_analysis(user_id=user_id, mode=mode)
        
        # Ensure we have results before building response
        if not results and nexus_db.is_dynamo_enabled():
            # If fresh scan returned empty (e.g. TwelveData partial outage), try stale cache fallback
            stale = nexus_db.get_latest_analysis_results(user_id, mode.value, max_age_seconds=7200) # 2 hours
            if stale:
                age_min = _cache_age_minutes(stale)
                logger.warning(f"Fresh scan empty, falling back to STALE cache for {user_id} (age={age_min}m)")
                resp = AnalysisResponse(**stale)
                resp.is_stale = True
                resp.served_from_cache = True
                resp.data_age_minutes = age_min
                return _scrub_nans(resp.dict())

        response = AnalysisResponse(
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            instruments=results,
            weekly_performance=perf,
            correlation_data=corr,
            psychological_guardrail=guardrail,
            is_stale=False,
            served_from_cache=False,
            data_age_minutes=0
        )

        # Save to Cache
        if nexus_db.is_dynamo_enabled() and results:
            try:
                nexus_db.save_analysis_results(user_id, _scrub_nans(response.dict()), mode.value)
            except Exception as e:
                logger.error(f"Failed to cache analysis: {e}")

        # Send Telegram alerts for high-intent signals (scheduler path only)
        if user_id == "global_default" and results:
            try:
                from .notifier import send_alerts
                from .config_loader import load_config, get_alert_config
                cfg = load_config(user_id=user_id)
                alert_cfg = get_alert_config(cfg)
                for inst in results:
                    try:
                        send_alerts(inst, alert_cfg)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"[NOTIFIER] Telegram alert send failed: {e}")

        return _scrub_nans(response.dict())

    except Exception as e:
        logger.error(f"Analysis Failed for {user_id}: {e}")
        # 3. Emergency Fallback: Serve ANY cache available for this user (up to 4 hours)
        if nexus_db.is_dynamo_enabled():
            emergency_stale = nexus_db.get_latest_analysis_results(user_id, mode.value, max_age_seconds=14400)
            if emergency_stale:
                age_min = _cache_age_minutes(emergency_stale)
                logger.info(f"Returning EMERGENCY STALE data for {user_id} (age={age_min}m) due to error: {e}")
                resp = AnalysisResponse(**emergency_stale)
                resp.is_stale = True
                resp.served_from_cache = True
                resp.data_age_minutes = age_min
                return _scrub_nans(resp.dict())
            
            # 4. Final Fallback: Serve the GLOBAL DEFAULT cache so the UI isn't blank for new users
            global_stale = nexus_db.get_latest_analysis_results("global_default", mode.value, max_age_seconds=14400)
            if global_stale:
                age_min = _cache_age_minutes(global_stale)
                logger.info(f"Returning GLOBAL DEFAULT cache for {user_id} (age={age_min}m) (fallback)")
                resp = AnalysisResponse(**global_stale)
                resp.is_stale = True
                resp.served_from_cache = True
                resp.data_age_minutes = age_min
                return _scrub_nans(resp.dict())
        
        # If absolutely nothing works, raise the error
        raise HTTPException(status_code=503, detail="Market analysis currently unavailable. System is performing a fresh scan, please retry in 30 seconds.")

@app.get("/api/analyze/{symbol}")
async def analyze_single(symbol: str, mode: Any = None, user_id: str = Depends(get_current_user)):
    from .config_loader import load_config, get_instruments, get_analysis_params, get_strategy_config
    from .models import StrategySettings, StrategyMode, Signal
    from .data_fetcher import fetch_historical_data
    from .analyzers import analyze_monthly_trend
    
    # Cast mode if string
    if isinstance(mode, str):
        mode = StrategyMode(mode)
    if mode is None:
        mode = StrategyMode.LONG_TERM
    
    config = load_config(user_id=user_id)
    params = get_analysis_params(config)
    instruments = get_instruments(config)
    strategy_settings = StrategySettings(**get_strategy_config(config))
    
    name = symbol
    for inst in instruments:
        if inst['symbol'].upper() == symbol.upper():
            name = inst['name']
            break

    # Fetch Benchmarks in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_spy = executor.submit(fetch_historical_data, "SPX", days=1000, interval=("1month" if mode == StrategyMode.LONG_TERM else "1day"))
        f_dxy = executor.submit(fetch_historical_data, "DXY", days=30, interval="1day")
        f_tnx = executor.submit(fetch_historical_data, "TNX", days=30, interval="1day")
        
        spy_df = f_spy.result()
        dxy_df = f_dxy.result()
        tnx_df = f_tnx.result()
    
    spy_bench_info = analyze_monthly_trend(spy_df, params.get('monthly', {}))
    
    analysis, _ = analyze_instrument_lazy(
        symbol.upper(), name, params, spy_bench_info.direction, strategy_settings, 
        mode=mode, dxy_df=dxy_df, us10y_df=tnx_df
    )
    return analysis

@app.get("/api/instruments")
async def list_instruments(user_id: str = Depends(get_current_user)):
    from .config_loader import load_config, get_instruments
    config = load_config(user_id=user_id)
    return {"instruments": get_instruments(config)}

@app.post("/api/instruments")
async def add_instrument(instrument_data: Dict[str, str], user_id: str = Depends(get_current_user)):
    from .config_loader import load_config, get_instruments, save_instruments, BENCHMARK_ONLY_SYMBOLS
    from .symbol_validator import validate_symbol
    config = load_config(user_id=user_id)
    instruments = get_instruments(config)
    
    if len(instruments) >= 5:
        raise HTTPException(status_code=400, detail="Maximum limit of 5 instruments reached. Please remove an instrument before adding a new one.")
    
    symbol = instrument_data.get("symbol", "").upper()
    name = instrument_data.get("name", "")

    # Check if symbol is a benchmark (internal use only)
    if symbol in BENCHMARK_ONLY_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"{symbol} is a benchmark used internally and cannot be added as a user instrument.")
    
    # Check for duplicates
    if any(i['symbol'].upper() == symbol for i in instruments):
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} already exists")
    
    # Validate symbol against data provider
    validation = validate_symbol(symbol)
    if not validation['valid']:
        raise HTTPException(
            status_code=400, 
            detail=validation['message']
        )
    
    # Use the corrected symbol if validation suggested one
    final_symbol = validation['symbol']
    final_name = name or final_symbol
    
    # Add the instrument
    instruments.append({"symbol": final_symbol, "name": final_name})
    save_instruments(instruments, user_id=user_id)
    
    response = {
        "message": f"Instrument {final_symbol} added successfully",
        "instruments": instruments
    }
    
    # Include correction message if symbol was auto-corrected
    if validation['message']:
        response['note'] = validation['message']
    
    return response

@app.get("/api/instruments/validate/{symbol}")
async def validate_instrument_symbol(symbol: str):
    """Validate a symbol against the data provider before adding."""
    from .symbol_validator import validate_symbol
    from .config_loader import BENCHMARK_ONLY_SYMBOLS
    
    symbol_upper = symbol.upper()
    
    # Check if symbol is a benchmark
    if symbol_upper in BENCHMARK_ONLY_SYMBOLS:
        return {
            "valid": False,
            "symbol": symbol_upper,
            "message": f"{symbol_upper} is a benchmark used internally and cannot be added as a user instrument.",
            "suggestions": []
        }
    
    # Validate against data provider
    validation = validate_symbol(symbol_upper)
    return validation

@app.post("/api/instruments/reset")
async def reset_instruments(user_id: str = Depends(get_current_user)):
    """Reset instrument list to the four default symbols (XAU, XAG, WTI, BTC)."""
    from .config_loader import load_config, save_instruments, DEFAULT_INSTRUMENTS
    config = load_config(user_id=user_id)
    save_instruments(list(DEFAULT_INSTRUMENTS), user_id=user_id)
    return {"message": "Instruments reset to defaults", "instruments": DEFAULT_INSTRUMENTS}

@app.delete("/api/instruments/{symbol}")
async def delete_instrument(symbol: str, user_id: str = Depends(get_current_user)):
    from .config_loader import load_config, get_instruments, save_instruments
    config = load_config(user_id=user_id)
    instruments = get_instruments(config)
    
    new_instruments = [i for i in instruments if i['symbol'].upper() != symbol.upper()]
    if len(new_instruments) == len(instruments):
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
    save_instruments(new_instruments, user_id=user_id)
    return {"message": f"Instrument {symbol} removed successfully", "instruments": new_instruments}

@app.get("/api/settings")
async def get_settings(user_id: str = Depends(get_current_user)):
    """Get strategy settings — DynamoDB first, then YAML config."""
    # Try DynamoDB for user-specific overrides
    if nexus_db.is_dynamo_enabled():
        try:
            saved = nexus_db.get_settings(user_id)
            if saved and 'strategy' in saved:
                return saved['strategy']
        except Exception as e:
            logger.error(f"DynamoDB settings read failed: {e}")

    # Fallback to YAML config
    from .config_loader import load_config, get_strategy_config
    config = load_config(user_id=user_id)
    return get_strategy_config(config)

@app.post("/api/settings")
async def update_settings(settings: Dict[str, Any], user_id: str = Depends(get_current_user)):
    """Save strategy settings — DynamoDB + YAML config."""
    # Save to DynamoDB (user-specific)
    if nexus_db.is_dynamo_enabled():
        try:
            existing = nexus_db.get_settings(user_id) or {}
            existing['strategy'] = settings
            nexus_db.save_settings(user_id, existing)
            logger.info(f"Strategy settings saved to DynamoDB for {user_id}")
        except Exception as e:
            logger.error(f"DynamoDB settings save failed: {e}")

    # Also save to YAML/S3 config (backward compat)
    from .config_loader import save_strategy_config
    save_strategy_config(settings, user_id=user_id)
    return {"message": "Strategy settings updated successfully"}

# ─── User Preferences ────────────────────────────────────────────

@app.get("/api/preferences")
async def get_preferences(user_id: str = Depends(get_current_user)):
    """Get all user preferences — theme, display, notifications, strategy."""
    defaults = {
        "theme": "dark",
        "view_mode": "heatmap",       # heatmap | list
        "strategy_mode": "long_term", # long_term | short_term
        "auto_refresh": True,
        "refresh_interval": 900,      # seconds (15 min)
        "show_news": True,
        "show_copilot": True,
        "notifications": {
            "enabled": False,
            "trade_worthy_alerts": True,
            "pullback_warnings": True,
            "score_threshold": 50,
        },
        "strategy": {
            "conviction_threshold": 70,
            "adx_threshold": 25,
            "atr_multiplier_tp": 3.0,
            "atr_multiplier_sl": 1.5,
            "portfolio_value": 10000.0,
            "risk_per_trade_percent": 1.0,
            "aggressiveness_mode": "balanced",
        }
    }

    if nexus_db.is_dynamo_enabled():
        try:
            saved = nexus_db.get_settings(user_id)
            if saved:
                # Merge saved over defaults (deep merge)
                for key in defaults:
                    if key in saved:
                        if isinstance(defaults[key], dict) and isinstance(saved[key], dict):
                            defaults[key].update(saved[key])
                        else:
                            defaults[key] = saved[key]
                return defaults
        except Exception as e:
            logger.error(f"DynamoDB preferences read failed: {e}")

    # Fallback: load strategy from YAML, return rest as defaults
    from .config_loader import load_config, get_strategy_config
    config = load_config(user_id=user_id)
    defaults['strategy'] = get_strategy_config(config)
    return defaults

@app.put("/api/preferences")
async def update_preferences(request: Request, user_id: str = Depends(get_current_user)):
    """Update user preferences (partial update supported)."""
    prefs = await request.json()

    if nexus_db.is_dynamo_enabled():
        try:
            existing = nexus_db.get_settings(user_id) or {}
            # Merge incoming prefs into existing
            for key, value in prefs.items():
                if isinstance(value, dict) and isinstance(existing.get(key), dict):
                    existing[key].update(value)
                else:
                    existing[key] = value
            nexus_db.save_settings(user_id, existing)
            logger.info(f"Preferences saved to DynamoDB for {user_id}")
            return {"message": "Preferences updated", "preferences": existing}
        except Exception as e:
            logger.error(f"DynamoDB preferences save failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")
    else:
        # Fallback: only save strategy to YAML
        if 'strategy' in prefs:
            from .config_loader import save_strategy_config
            save_strategy_config(prefs['strategy'], user_id=user_id)
        return {"message": "Preferences updated (strategy only, DynamoDB not available)", "preferences": prefs}

@app.get("/api/chart/{symbol}")
async def get_chart_data(symbol: str):
    from .data_fetcher import fetch_historical_data
    try:
        df = fetch_historical_data(symbol, days=365)
        # Convert to list of dicts for frontend
        data = []
        for index, row in df.iterrows():
            data.append({
                "time": index.strftime('%Y-%m-%d'),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": float(row['Volume'])
            })
        return data
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {e}")
        return {"error": str(e)}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/debug/telegram")
async def debug_telegram(send_test: bool = False, user_id: str = Depends(get_current_user)):
    """
    Diagnostic endpoint to verify Telegram configuration.
    Pass ?send_test=true to actually fire a test message to the configured chat.
    """
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    result = {
        "TELEGRAM_BOT_TOKEN": "SET" if token else "MISSING",
        "TELEGRAM_CHAT_ID":   "SET" if chat_id else "MISSING",
        "token_prefix":       token[:10] + "..." if token else None,
        "chat_id":            chat_id if chat_id else None,
        "test_sent":          False,
        "test_error":         None,
    }
    if send_test and token and chat_id:
        try:
            import requests as _req
            resp = _req.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text":    f"✅ *Market Analyser — Telegram Test*\nSent at `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}`",
                    "parse_mode": "Markdown",
                },
                timeout=8,
            )
            result["test_sent"]         = resp.status_code == 200
            result["telegram_response"] = resp.json()
        except Exception as e:
            result["test_error"] = str(e)
    elif send_test:
        result["test_error"] = "Cannot send — one or both env vars missing"
    return result

@app.get("/api/test/gold")
async def test_gold():
    from .models import StrategySettings, Signal
    from .config_loader import load_config, get_analysis_params, get_strategy_config
    
    config = load_config()
    params = get_analysis_params(config)
    strategy_settings = StrategySettings(**get_strategy_config(config))
    
    try:
        # Pass Signal.NEUTRAL to avoid validation error
        analysis, _ = analyze_instrument_lazy("XAU", "Gold USD Test", params, benchmark_direction=Signal.NEUTRAL, strategy_settings=strategy_settings)
        return {
            "analysis": analysis
        }
    except Exception as e:
        import traceback
        logger.error(f"Test Gold Failed: {e}\n{traceback.format_exc()}")
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

# ─── Trade Journal ────────────────────────────────────────────────
import uuid
from . import db as nexus_db

def _load_journal(user_id: str = "global_default") -> list:
    """Load trade journal — DynamoDB first, then S3, then local file."""
    # DynamoDB (preferred)
    if nexus_db.is_dynamo_enabled():
        try:
            trades = nexus_db.get_trades(user_id)
            logger.info(f"Loaded {len(trades)} trades from DynamoDB for {user_id}")
            return trades
        except Exception as e:
            logger.error(f"DynamoDB read failed, falling back to S3: {e}")

    # S3 fallback (for production until DynamoDB migration is complete)
    import json
    from pathlib import Path
    
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        import boto3
        s3 = boto3.client('s3')
        bucket = os.environ.get('CONFIG_S3_BUCKET') or os.environ.get('CONFIG_BUCKET')
        if not bucket:
            logger.error("Neither CONFIG_S3_BUCKET nor CONFIG_BUCKET environment variable is set")
            return []
        key = f"users/{user_id}/trade_journal.json"
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            return json.loads(obj['Body'].read().decode('utf-8'))
        except:
            return []
    else:
        # Local file (development)
        path = Path(__file__).parent.parent / "cache" / f"journal_{user_id}.json"
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return []

def _save_journal_legacy(trades: list, user_id: str = "global_default"):
    """Save trade journal to S3 or local file (legacy fallback)."""
    import json
    from pathlib import Path
    
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        import boto3
        s3 = boto3.client('s3')
        bucket = os.environ.get('CONFIG_S3_BUCKET') or os.environ.get('CONFIG_BUCKET')
        if not bucket:
            logger.error("Bucket configuration missing for journal save")
            return
        key = f"users/{user_id}/trade_journal.json"
        s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(trades), ContentType='application/json')
    else:
        path = Path(__file__).parent.parent / "cache" / f"journal_{user_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(trades, f)

@app.get("/api/journal")
async def get_journal(user_id: str = Depends(get_current_user)):
    return _load_journal(user_id)

@app.post("/api/journal")
async def add_trade(request: Request, user_id: str = Depends(get_current_user)):
    trade = await request.json()
    trade["id"] = str(uuid.uuid4())
    trade["created_at"] = datetime.now(timezone.utc).isoformat()

    # DynamoDB (preferred)
    if nexus_db.is_dynamo_enabled():
        try:
            saved = nexus_db.save_trade(user_id, trade)
            logger.info(f"Trade saved to DynamoDB: {trade['id']}")
            return {"message": "Trade logged", "trade": trade}
        except Exception as e:
            logger.error(f"DynamoDB save failed, falling back to S3: {e}")

    # Fallback: S3/local
    trades = _load_journal(user_id)
    trades.append(trade)
    _save_journal_legacy(trades, user_id)
    return {"message": "Trade logged", "trade": trade}

@app.delete("/api/journal/{trade_id}")
async def delete_trade(trade_id: str, user_id: str = Depends(get_current_user)):
    # DynamoDB (preferred)
    if nexus_db.is_dynamo_enabled():
        try:
            nexus_db.delete_trade(user_id, trade_id)
            logger.info(f"Trade deleted from DynamoDB: {trade_id}")
            return {"message": "Trade removed"}
        except Exception as e:
            logger.error(f"DynamoDB delete failed, falling back to S3: {e}")

    # Fallback: S3/local
    trades = _load_journal(user_id)
    trades = [t for t in trades if t.get("id") != trade_id]
    _save_journal_legacy(trades, user_id)
    return {"message": "Trade removed"}

# ─── Admin: Migration & Status ───────────────────────────────────

@app.get("/api/db-status")
async def db_status():
    """Check which storage backend is active."""
    return {
        "dynamodb_enabled": nexus_db.is_dynamo_enabled(),
        "dynamodb_table": os.environ.get('DYNAMODB_TABLE', 'not set'),
        "s3_bucket": os.environ.get('CONFIG_S3_BUCKET', 'not set'),
        "environment": os.environ.get('ENVIRONMENT', 'local'),
    }

@app.post("/api/admin/migrate-journal")
async def migrate_journal_to_dynamodb(user_id: str = Depends(get_current_user)):
    """One-time migration: copy trades from S3 to DynamoDB."""
    if not nexus_db.is_dynamo_enabled():
        raise HTTPException(status_code=400, detail="DynamoDB not configured")
    
    # Load from S3 (legacy)
    import json
    s3_trades = []
    if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
        import boto3
        s3 = boto3.client('s3')
        bucket = os.environ.get('CONFIG_S3_BUCKET') or os.environ.get('CONFIG_BUCKET')
        if not bucket:
            return {"message": "Bucket configuration missing", "migrated": 0}
        key = f"users/{user_id}/trade_journal.json"
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            s3_trades = json.loads(obj['Body'].read().decode('utf-8'))
        except:
            pass
    
    if not s3_trades:
        return {"message": "No S3 trades to migrate", "migrated": 0}
    
    # Write each to DynamoDB
    migrated = 0
    for trade in s3_trades:
        try:
            nexus_db.save_trade(user_id, trade)
            migrated += 1
        except Exception as e:
            logger.error(f"Failed to migrate trade {trade.get('id')}: {e}")
    
    return {
        "message": f"Migrated {migrated}/{len(s3_trades)} trades to DynamoDB",
        "migrated": migrated,
        "total": len(s3_trades)
    }

# ──────────────────────────────────────────────────────────────────────────────
# INTRADAY SIGNAL ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/signals")
async def get_signals(symbol: Optional[str] = None, limit: int = 50, user_id: str = Depends(get_current_user)):
    """Return latest intraday signals. Optionally filter by symbol."""
    from .signal_store import get_recent_signals, get_signals_for_symbol
    if symbol:
        signals = get_signals_for_symbol(symbol.upper(), limit=limit)
    else:
        signals = get_recent_signals(limit=limit)
    return {"signals": [s.model_dump() for s in signals], "count": len(signals)}


@app.get("/api/signals/stats")
async def get_signal_stats(user_id: str = Depends(get_current_user)):
    """Return aggregated signal performance stats across all recent signals."""
    from .signal_store import get_recent_signals
    signals = get_recent_signals(limit=200)

    total    = len(signals)
    active   = sum(1 for s in signals if s.status == "ACTIVE")
    tp_hits  = sum(1 for s in signals if s.status in ("HIT_TP1", "HIT_TP2"))
    tp2_hits = sum(1 for s in signals if s.status == "HIT_TP2")
    sl_hits  = sum(1 for s in signals if s.status == "HIT_SL")
    expired  = sum(1 for s in signals if s.status == "EXPIRED")
    closed   = tp_hits + sl_hits

    # Per-timeframe breakdown
    breakdown: dict = {}
    for tf in ("15m", "1H", "4H"):
        tf_sigs  = [s for s in signals if s.timeframe == tf]
        tf_tp    = sum(1 for s in tf_sigs if s.status in ("HIT_TP1", "HIT_TP2"))
        tf_sl    = sum(1 for s in tf_sigs if s.status == "HIT_SL")
        tf_closed = tf_tp + tf_sl
        breakdown[tf] = {
            "total":    len(tf_sigs),
            "tp_hits":  tf_tp,
            "sl_hits":  tf_sl,
            "win_rate": round(tf_tp / tf_closed * 100, 1) if tf_closed > 0 else None,
        }

    # Per-trigger breakdown
    triggers: dict = {}
    for sig in signals:
        base = sig.trigger.split("+")[0]
        if base not in triggers:
            triggers[base] = {"total": 0, "tp": 0, "sl": 0}
        triggers[base]["total"] += 1
        if sig.status in ("HIT_TP1", "HIT_TP2"):
            triggers[base]["tp"] += 1
        elif sig.status == "HIT_SL":
            triggers[base]["sl"] += 1

    return {
        "total":    total,
        "active":   active,
        "tp_hits":  tp_hits,
        "tp2_hits": tp2_hits,
        "sl_hits":  sl_hits,
        "expired":  expired,
        "win_rate": round(tp_hits / closed * 100, 1) if closed > 0 else None,
        "by_timeframe": breakdown,
        "by_trigger":   triggers,
    }


@app.post("/api/signals/scan")
async def scan_signals(user_id: str = Depends(get_current_user)):
    """
    Trigger an intraday signal scan across all configured instruments.
    Fetches 4H + 1H + 15m bars, runs EMA/MACD crossover detection,
    persists new signals to DynamoDB, and returns what was found.
    Also called automatically by EventBridge every 5 minutes.
    """
    from .analyzers.intraday_signal_generator import detect_intraday_signals_verbose
    from .signal_store import save_signal, expire_old_signals, check_signal_outcomes

    from .config_loader import load_config, get_instruments
    config = load_config(user_id=user_id)
    raw_instruments = get_instruments(config)
    instruments = [{"symbol": i["symbol"], "name": i.get("name", i["symbol"])} for i in raw_instruments]

    # Expire stale signals first
    expire_old_signals()

    from .twelvedata_fetcher import TwelveDataFetcher
    fetcher   = TwelveDataFetcher()
    sym_list  = [i["symbol"].upper() for i in instruments]

    # Fetch all three timeframes in parallel
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_4h  = ex.submit(fetcher.fetch_batch_data, sym_list, interval="4h",  days=60)
        f_1h  = ex.submit(fetcher.fetch_batch_data, sym_list, interval="1h",  days=15)
        f_15m = ex.submit(fetcher.fetch_batch_data, sym_list, interval="15min", days=4)

    batch_4h  = f_4h.result()
    batch_1h  = f_1h.result()
    batch_15m = f_15m.result()

    all_signals = []
    diagnostics = []
    for inst in instruments:
        sym  = inst["symbol"].upper()
        name = inst.get("name", sym)
        try:
            new_signals, diag = detect_intraday_signals_verbose(
                symbol   = sym,
                name     = name,
                bars_4h  = batch_4h.get(sym),
                bars_1h  = batch_1h.get(sym),
                bars_15m = batch_15m.get(sym),
            )
            diagnostics.append(diag)
            saved = 0
            for sig in new_signals:
                if save_signal(sig):
                    saved += 1
                    all_signals.append(sig.model_dump())
                    # Telegram notification for new signals
                    _notify_intraday_signal(sig)
            if new_signals:
                logger.info(f"[SCAN] {sym}: {len(new_signals)} signals detected, {saved} new saved")
        except Exception as e:
            logger.warning(f"[SCAN] {sym} failed: {e}")
            diagnostics.append({"symbol": sym, "bias_4h": "unknown", "bias_1h": "unknown",
                                "skip_reasons": [f"scan failed: {e}"]})

    # ── TP / SL outcome tracking ──────────────────────────────────────────────
    # Extract current prices from the 1H batch (last closed bar)
    current_prices: dict = {}
    for sym in sym_list:
        bars_1h = batch_1h.get(sym)
        if bars_1h is not None and len(bars_1h) > 1:
            current_prices[sym] = float(bars_1h["Close"].iloc[-2])

    outcomes = check_signal_outcomes(current_prices)
    for outcome in outcomes:
        sig        = outcome["signal"]
        new_status = outcome["new_status"]
        _notify_signal_outcome(sig, new_status)
        logger.info(f"[SCAN] {sig.symbol} {sig.timeframe} outcome: {new_status}")

    return {
        "scanned":     len(instruments),
        "new_signals": len(all_signals),
        "signals":     all_signals,
        "diagnostics": diagnostics,
        "outcomes":    [{"symbol": o["signal"].symbol, "timeframe": o["signal"].timeframe,
                         "signal_type": o["signal"].signal_type, "status": o["new_status"]}
                        for o in outcomes],
    }


def _notify_intraday_signal(sig: "IntradaySignal"):
    """Send Telegram notification for a new intraday signal."""
    token    = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id  = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        import requests as _req
        emoji = "🟢" if sig.signal_type == "LONG" else "🔴"
        conf_stars = "⭐" * (1 + (sig.confidence - 50) // 15)
        quality = ""
        if "RSI_DIV" in sig.trigger and "WARN" not in sig.trigger:
            quality += "  ✨ RSI Divergence confirmed"
        if "RSI_DIV_WARN" in sig.trigger:
            quality += "  ⚠️ RSI Divergence opposes"
        if "PIN_BAR" in sig.trigger:
            quality += "  📌 Pin bar"
        text = (
            f"{emoji} *{sig.signal_type} SIGNAL — {sig.symbol} {sig.timeframe}*\n"
            f"📌 Trigger: `{sig.trigger.split('+')[0]}`  {conf_stars} ({sig.confidence}%){quality}\n"
            f"🎯 Entry:  `{sig.entry_price}`\n"
            f"🛑 SL:     `{sig.stop_loss}`\n"
            f"✅ TP1:    `{sig.take_profit_1}`   TP2: `{sig.take_profit_2}`\n"
            f"📊 R:R     `{sig.risk_reward}:1`   4H bias: `{sig.mtf_bias.upper()}`\n"
            f"⏰ Expires: `{sig.expires_at[:16]} UTC`"
        )
        _req.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"[SIGNAL_NOTIFY] Telegram failed: {e}")


def _notify_signal_outcome(sig: "IntradaySignal", new_status: str):
    """Send Telegram notification when a signal hits TP or SL."""
    token   = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        import requests as _req
        if new_status == "HIT_SL":
            emoji, label = "🔴", "STOP LOSS HIT"
        elif new_status == "HIT_TP2":
            emoji, label = "🏆", "TP2 HIT — FULL TARGET"
        elif new_status == "HIT_TP1":
            emoji, label = "✅", "TP1 HIT — PARTIAL TARGET"
        else:
            return

        dir_emoji = "🟢 LONG" if sig.signal_type == "LONG" else "🔴 SHORT"
        text = (
            f"{emoji} *{label}*\n"
            f"{dir_emoji} {sig.symbol} {sig.timeframe} — `{sig.trigger.split('+')[0]}`\n"
            f"Entry: `{sig.entry_price}` → {new_status}\n"
            f"SL: `{sig.stop_loss}`  TP1: `{sig.take_profit_1}`  TP2: `{sig.take_profit_2}`"
        )
        _req.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"[OUTCOME_NOTIFY] Telegram failed: {e}")


@app.get("/api/swing-reversal/{symbol}")
async def get_swing_reversal(symbol: str, user_id: str = Depends(get_current_user)):
    """
    Analyze swing trade reversal opportunities using divergence detection.
    Detects RSI, MACD, and MA divergences across multiple timeframes.
    """
    from .analyzers.swing_reversal_analyzer import analyze_swing_reversal
    from .data_fetcher import fetch_historical_data
    
    try:
        # Fetch daily data (primary timeframe)
        df_daily = fetch_historical_data(symbol, interval='1day', days=200)
        
        # Fetch 4H data for confirmation (optional)
        df_4h = None
        try:
            df_4h = fetch_historical_data(symbol, interval='4h', days=100)
        except Exception as e:
            logger.warning(f"Failed to fetch 4H data for {symbol}: {e}")
        
        # Fetch weekly data for major signals (optional)
        df_weekly = None
        try:
            df_weekly = fetch_historical_data(symbol, interval='1week', days=100)
        except Exception as e:
            logger.warning(f"Failed to fetch weekly data for {symbol}: {e}")
        
        # Analyze reversal
        analysis = analyze_swing_reversal(symbol, df_daily, df_4h, df_weekly)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in swing reversal analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# PYRAMID POSITION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/pyramid/position")
async def create_pyramid_position(
    position_data: dict,
    user_id: str = Depends(get_current_user)
):
    """Create a new pyramid position."""
    from app.models import PyramidPosition
    from app.db import save_trade
    import uuid
    from datetime import datetime, timezone
    
    try:
        position_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        position = PyramidPosition(
            id=position_id,
            user_id=user_id,
            symbol=position_data['symbol'].upper(),
            direction=position_data['direction'],
            entry_price=float(position_data['entry_price']),
            initial_lots=int(position_data['initial_lots']),
            current_lots=int(position_data['initial_lots']),
            current_stop_loss=float(position_data['stop_loss']),
            current_price=float(position_data['entry_price']),
            unrealized_pnl=0.0,
            created_at=now,
            updated_at=now,
            pyramid_level=1,
            status='active'
        )
        
        # Save to DynamoDB
        trade_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        save_trade(user_id, {
            'id': position_id,
            'date': trade_date,
            'symbol': position.symbol,
            'direction': position.direction,
            'entry_price': position.entry_price,
            'initial_lots': position.initial_lots,
            'lots': position.current_lots,
            'stop_loss': position.current_stop_loss,
            'type': 'pyramid',
            'created_at': now,
            'updated_at': now,
            'pyramid_level': 1,
            'status': 'active'
        })
        
        return position.model_dump()
        
    except Exception as e:
        logger.error(f"Error creating pyramid position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pyramid/positions")
async def get_pyramid_positions(user_id: str = Depends(get_current_user)):
    """Get all pyramid positions for user."""
    from app.db import get_trades
    
    try:
        trades = get_trades(user_id)
        pyramid_trades = [t for t in trades if t.get('type') == 'pyramid' and t.get('status') == 'active']
        
        # Update current prices
        from app.data_fetcher import get_current_price
        for trade in pyramid_trades:
            try:
                current_price = get_current_price(trade['symbol'])
                trade['current_price'] = current_price
                
                # Calculate unrealized PnL
                if trade['direction'] == 'long':
                    trade['unrealized_pnl'] = (current_price - trade['entry_price']) * trade['lots']
                else:
                    trade['unrealized_pnl'] = (trade['entry_price'] - current_price) * trade['lots']
            except Exception as e:
                logger.warning(f"Failed to get current price for {trade['symbol']}: {e}")
        
        return {"positions": pyramid_trades, "count": len(pyramid_trades)}
        
    except Exception as e:
        logger.error(f"Error getting pyramid positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pyramid/position/{position_id}/plan")
async def get_pyramid_plan(
    position_id: str,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    """Get pyramid plan for a specific position."""
    from app.db import get_trades
    from app.data_fetcher import fetch_historical_data, get_current_price
    from app.analyzers.volatility_analyzer import calculate_atr

    try:
        logger.info(f"Getting pyramid plan for position {position_id}")
        trading_style = request.query_params.get('trading_style', 'swing')
        logger.info(f"Trading style: {trading_style}")

        trades = get_trades(user_id)
        logger.info(f"Found {len(trades)} trades for user {user_id}")

        position_data = next((t for t in trades if t['id'] == position_id), None)

        if not position_data:
            logger.error(f"Position {position_id} not found in trades")
            raise HTTPException(status_code=404, detail="Position not found")

        logger.info(f"Found position data: {position_data}")

        # Get current price
        current_price = get_current_price(position_data['symbol'])
        logger.info(f"Current price: {current_price}")

        # Get ATR for volatility
        df = fetch_historical_data(position_data['symbol'], interval='1day', days=50)
        atr = calculate_atr(df, period=14)
        logger.info(f"ATR: {atr}")

        # Create PyramidPosition model with defaults for missing fields
        from app.models import PyramidPosition
        position = PyramidPosition(
            id=position_data['id'],
            user_id=user_id,
            symbol=position_data['symbol'],
            direction=position_data['direction'],
            entry_price=position_data['entry_price'],
            initial_lots=position_data.get('initial_lots', position_data.get('lots', 1)),
            current_lots=position_data.get('lots', position_data.get('initial_lots', 1)),
            current_stop_loss=position_data.get('stop_loss', 0),
            current_price=current_price,
            unrealized_pnl=position_data.get('unrealized_pnl', 0.0),
            created_at=position_data.get('created_at', ''),
            updated_at=position_data.get('updated_at', position_data.get('created_at', '')),
            pyramid_level=position_data.get('pyramid_level', 1),
            status=position_data.get('status', 'active')
        )

        # Calculate pyramid plan
        from app.analyzers.pyramid_calculator import calculate_pyramid_plan
        plan = calculate_pyramid_plan(position, atr, current_price, trading_style=trading_style)
        logger.info(f"Pyramid plan calculated successfully")

        return plan.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pyramid plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/pyramid/position/{position_id}")
async def delete_pyramid_position(
    position_id: str,
    action: str = "soft",  # 'soft' for history, 'hard' for permanent
    user_id: str = Depends(get_current_user)
):
    """Delete pyramid position (soft delete to history or hard delete)."""
    from app.db import get_trades, _get_table

    try:
        logger.info(f"Deleting pyramid position {position_id} with action {action}")
        trades = get_trades(user_id)
        logger.info(f"Found {len(trades)} trades for user {user_id}")

        position = next((t for t in trades if t['id'] == position_id), None)

        if position is None:
            logger.error(f"Position {position_id} not found in trades")
            raise HTTPException(status_code=404, detail="Position not found")

        logger.info(f"Found position: {position}")

        # Get the actual SK from the DynamoDB item (includes PK and SK from cleaned item)
        # We need to query DynamoDB directly to get the actual PK/SK
        table = _get_table()

        # Scan for the item with the given ID
        response = table.scan(
            FilterExpression='id = :id AND PK = :pk',
            ExpressionAttributeValues={
                ':id': position_id,
                ':pk': f"USER#{user_id}"
            }
        )

        items = response.get('Items', [])
        if not items:
            logger.error(f"Position {position_id} not found in DynamoDB scan")
            raise HTTPException(status_code=404, detail="Position not found in DynamoDB")

        # Use the first matching item (there should only be one)
        item = items[0]
        pk = item['PK']
        sk = item['SK']
        logger.info(f"Deleting item with PK={pk}, SK={sk}")

        if action == "soft":
            # Soft delete: update status to history in DynamoDB
            table.update_item(
                Key={'PK': pk, 'SK': sk},
                UpdateExpression="SET #status = :status, #updated_at = :updated_at",
                ExpressionAttributeNames={
                    '#status': 'status',
                    '#updated_at': 'updated_at'
                },
                ExpressionAttributeValues={
                    ':status': 'history',
                    ':updated_at': datetime.now().isoformat()
                }
            )
            logger.info(f"Position {position_id} moved to history")
            return {"message": "Position moved to history", "action": "soft_delete"}
        elif action == "hard":
            # Hard delete: remove from DynamoDB
            table.delete_item(Key={'PK': pk, 'SK': sk})
            logger.info(f"Position {position_id} permanently deleted")
            return {"message": "Position permanently deleted", "action": "hard_delete"}
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'soft' or 'hard'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pyramid position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/pyramid/position/{position_id}")
async def update_pyramid_position(
    position_id: str,
    updates: dict,
    user_id: str = Depends(get_current_user)
):
    """Update pyramid position (edit entry price, lots, etc.)."""
    from app.db import get_trades, _get_table

    try:
        trades = get_trades(user_id)
        position = next((t for t in trades if t['id'] == position_id), None)

        if position is None:
            raise HTTPException(status_code=404, detail="Position not found")

        # Allowed fields to update
        allowed_fields = ['entry_price', 'initial_lots', 'lots', 'stop_loss', 'direction', 'status']

        # Build update expression dynamically
        update_expressions = []
        expression_names = {}
        expression_values = {}

        for field, value in updates.items():
            if field in allowed_fields:
                update_expressions.append(f"#{field} = :{field}")
                expression_names[f"#{field}"] = field
                expression_values[f":{field}"] = value

        if not update_expressions:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Add updated_at
        update_expressions.append("#updated_at = :updated_at")
        expression_names["#updated_at"] = "updated_at"
        expression_values[":updated_at"] = datetime.now().isoformat()

        # Get actual PK/SK from DynamoDB by scanning
        table = _get_table()
        response = table.scan(
            FilterExpression='id = :id AND PK = :pk',
            ExpressionAttributeValues={
                ':id': position_id,
                ':pk': f"USER#{user_id}"
            }
        )

        items = response.get('Items', [])
        if not items:
            raise HTTPException(status_code=404, detail="Position not found in DynamoDB")

        item = items[0]
        pk = item['PK']
        sk = item['SK']
        logger.info(f"Updating item with PK={pk}, SK={sk}")

        # Direct DynamoDB update
        table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression="SET " + ", ".join(update_expressions),
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values
        )

        logger.info(f"Position {position_id} updated successfully")
        return {"message": "Position updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pyramid position: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pyramid/positions/history")
async def get_pyramid_history(user_id: str = Depends(get_current_user)):
    """Get pyramid positions in history (soft deleted)."""
    from app.db import get_trades
    
    try:
        trades = get_trades(user_id)
        history_trades = [t for t in trades if t.get('type') == 'pyramid' and t.get('status') == 'history']
        
        return {"positions": history_trades, "count": len(history_trades)}
        
    except Exception as e:
        logger.error(f"Error getting pyramid history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pyramid/opportunities")
async def get_pyramid_opportunities(user_id: str = Depends(get_current_user)):
    """Get potential pyramid trading opportunities based on swing reversal detection."""
    from app.analyzers.swing_reversal_analyzer import analyze_swing_reversal
    from app.analyzers.pyramid_calculator import calculate_pyramid_plan
    from app.data_fetcher import fetch_historical_data, get_current_price
    from app.analyzers.volatility_analyzer import calculate_atr
    from app.config_loader import get_instruments, load_config, get_price_offset
    import pandas as pd
    
    try:
        config = load_config(user_id=user_id)
        instruments = get_instruments(config)
        opportunities = []
        
        for inst in instruments:
            symbol = inst['symbol']
            
            try:
                # Get swing reversal analysis
                df_daily = fetch_historical_data(symbol, interval='1day', days=200)
                df_4h = fetch_historical_data(symbol, interval='4h', days=100)
                
                reversal = analyze_swing_reversal(symbol, df_daily, df_4h)
                
                # Only consider if reversal detected with good confidence
                if reversal['reversal_detected'] and reversal.get('primary_signal'):
                    primary_signal = reversal['primary_signal']
                    
                    if primary_signal.get('confidence', 0) >= 0.6:
                        current_price = get_current_price(symbol)
                        atr = calculate_atr(df_daily, period=14)
                        
                        # Apply price offset for local market
                        price_offset = get_price_offset(config, symbol)
                        adjusted_price = current_price + price_offset
                        
                        # Calculate hypothetical pyramid plan with adjusted price
                        from app.models import PyramidPosition
                        hypothetical_position = PyramidPosition(
                            id="hypothetical",
                            user_id=user_id,
                            symbol=symbol,
                            direction=primary_signal['direction'],
                            entry_price=adjusted_price,
                            initial_lots=1,  # Base calculation on 1 lot
                            current_lots=1,
                            current_stop_loss=adjusted_price - (2 * atr) if primary_signal['direction'] == 'long' else adjusted_price + (2 * atr),
                            current_price=adjusted_price,
                            unrealized_pnl=0.0,
                            created_at="",
                            updated_at="",
                            pyramid_level=1,
                            status='active'
                        )
                        
                        plan = calculate_pyramid_plan(hypothetical_position, atr, adjusted_price)
                        
                        opportunities.append({
                            'symbol': symbol,
                            'name': inst.get('name', symbol),
                            'direction': primary_signal['direction'],
                            'current_price': adjusted_price,
                            'original_price': current_price,  # Show US reference price
                            'price_offset': price_offset,
                            'entry_range': {
                                'low': adjusted_price - (0.5 * atr),
                                'high': adjusted_price + (0.5 * atr)
                            },
                            'stop_loss': hypothetical_position.current_stop_loss,
                            'confidence': primary_signal['confidence'],
                            'divergence_sources': primary_signal.get('sources', []),
                            'pyramid_plan': {
                                'levels': plan.levels,
                                'total_risk': plan.total_risk,
                                'total_reward': plan.total_reward,
                                'risk_reward': plan.overall_risk_reward
                            },
                            'multi_timeframe': reversal.get('multi_timeframe', {}),
                            'risk_level': reversal.get('risk_level', 'MODERATE')
                        })
                        
            except Exception as e:
                logger.warning(f"Failed to analyze {symbol} for pyramid opportunities: {e}")
                continue
        
        # Sort by confidence and risk/reward
        opportunities.sort(key=lambda x: (x['confidence'], x['pyramid_plan']['risk_reward']), reverse=True)
        
        return {"opportunities": opportunities, "count": len(opportunities)}
        
    except Exception as e:
        logger.error(f"Error getting pyramid opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/pyramid/position/{position_id}")
async def close_pyramid_position(
    position_id: str,
    user_id: str = Depends(get_current_user)
):
    """Close a pyramid position."""
    from app.db import delete_trade, get_trades
    from datetime import datetime, timezone
    
    try:
        trades = get_trades(user_id)
        position = next((t for t in trades if t['id'] == position_id), None)
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        # Mark as closed
        position['status'] = 'closed'
        position['closed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Delete from active trades
        delete_trade(user_id, position_id)
        
        return {"message": "Position closed successfully", "position_id": position_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing pyramid position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Handler for AWS Lambda
handler = Mangum(app)
