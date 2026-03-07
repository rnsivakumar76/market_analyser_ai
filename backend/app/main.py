from fastapi import FastAPI, HTTPException, Depends, Request
from starlette.middleware.sessions import SessionMiddleware
from mangum import Mangum
from datetime import datetime, date, timezone
from typing import List, Dict, Any
import logging
import os
import traceback
from concurrent.futures import ThreadPoolExecutor

# Import auth dependencies - these are light
from .auth import get_current_user
from .oauth import router as auth_router
from .news.geopolitical_routes import router as geopolitical_router

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
        detect_opening_range, calculate_rvol, analyze_commodity_specifics, generate_expert_trade_plan
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
    # Override price change to be TRUE DAILY change
    # In Long Term mode, execution_data is 1d. In Short Term mode, macro_data is 1d.
    daily_source = execution_data if mode == StrategyMode.LONG_TERM else macro_data
    if not daily_source.empty and len(daily_source) >= 2:
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

    volatility = analyze_volatility_and_risk(execution_data, current_price, trend.direction.value, entry_price=ideal_entry)
    fundamentals = analyze_fundamentals(symbol)
    
    # NEW: Relative Strength Analysis (Alpha vs Beta)
    # Determine which benchmark to use
    is_crypto = any(sub in symbol.upper() for sub in ["BTC", "ETH", "CRYPTO", "BITCOIN"]) or (len(symbol) > 6 and "USD" in symbol.upper())
    bench_sym = "BTC" if is_crypto else "SPX"
    
    # Use pre-fetched data if available, otherwise fetch on the fly
    if benchmark_data_df is not None:
        bench_data = benchmark_data_df
    else:
        # Fetch benchmark data at the SAME execution interval
        bench_data = fetch_historical_data(
            bench_sym, 
            days=(500 if mode == StrategyMode.LONG_TERM else 20), 
            interval=("1day" if mode == StrategyMode.LONG_TERM else "1h")
        )
    
    rs_analysis = analyze_relative_strength(
        execution_data,
        bench_data,
        symbol,
        bench_sym,
        lookback_periods=20
    )
    
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
        relative_strength=rs_analysis
    )
    
    # NEW: Pullback Warning Logic
    pullback_warning = analyze_pullback_warning(execution_data, trend.direction)
    
    # Boost/adjust score based on technical indicators
    if tech_indicators.trend_breakout == 'bullish_breakout':
        trade_signal.score = min(trade_signal.score + 15, 100)
        trade_signal.reasons.append(f"Bullish Breakout ({tech_indicators.breakout_confidence*100:.0f}% confidence)")
    elif tech_indicators.trend_breakout == 'bearish_breakout':
        trade_signal.score = max(trade_signal.score - 15, -100)
        trade_signal.reasons.append(f"Bearish Breakout ({tech_indicators.breakout_confidence*100:.0f}% confidence)")

    # Adjust score based on pullback warning
    if pullback_warning.is_warning:
        # Penalize score if extended
        if trend.direction == Signal.BULLISH:
            trade_signal.score = max(trade_signal.score - 20, 0)
            trade_signal.reasons.append(f"Caution: {pullback_warning.description}")
        elif trend.direction == Signal.BEARISH:
            trade_signal.score = min(trade_signal.score + 20, 0)
            trade_signal.reasons.append(f"Caution: {pullback_warning.description}")

    # Boost/adjust based on news sentiment
    if news_sentiment.label == "Bullish":
        trade_signal.score = min(trade_signal.score + 10, 100)
        trade_signal.reasons.append(f"Positive News Sentiment (+10 boost)")
    elif news_sentiment.label == "Bearish":
        trade_signal.score = max(trade_signal.score - 10, -100)
        trade_signal.reasons.append(f"Negative News Sentiment (-10 penalty)")

    # Boost/adjust based on Relative Strength
    if rs_analysis.label == "Leader":
        trade_signal.score = min(trade_signal.score + 15, 100)
        trade_signal.reasons.append(f"Market Leader: Strong Relative Strength vs {bench_sym} (+15 boost)")
    elif rs_analysis.label == "Laggard":
        trade_signal.score = max(trade_signal.score - 15, -100)
        trade_signal.reasons.append(f"Market Laggard: Weak Relative Strength vs {bench_sym} (-15 penalty)")

    # Build expert plan now that trade_signal.recommendation is final and volatility.atr is available
    if _expert_or_data is not None:
        expert_plan = generate_expert_trade_plan(
            symbol, current_price, _expert_or_data, _expert_rvol, tech_indicators, _expert_advice,
            signal_direction=trade_signal.recommendation.value,
            atr=float(volatility.atr),
            rsi=float(strength.rsi),
            adx=float(strength.adx),
            session_ctx=session_ctx,
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
    ), execution_data

# In-memory store for sent alerts
SENT_ALERTS = set()

async def run_scheduled_analysis(user_id: str = "global_default", mode: Any = None):
    from .config_loader import load_config, get_instruments, get_analysis_params, get_alert_config, get_strategy_config, get_newsapi_key
    from .models import StrategySettings, Signal, StrategyMode
    from .data_fetcher import fetch_historical_data
    from .analyzers import (
        analyze_monthly_trend, calculate_weekly_performance, 
        calculate_correlations, apply_position_sizing, analyze_psychological_state
    )
    from .notifier import send_alerts
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
            "risk_per_trade_percent": 1.0
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

        # DXY / TNX consistently fail on free-tier API keys (symbol not recognised in batch).
        # Removing them eliminates ~4 wasted credit retries per scan.
        # Intermarket analysis degrades gracefully to None when not available.
        benchmarks_data = {
            "SPX_macro": b_macro.get("SPX"),
            "BTC_macro": b_macro.get("BTC"),
            "SPX_exec": b_exec.get("SPX"),
            "BTC_exec": b_exec.get("BTC"),
            "DXY": None,
            "US10Y": None
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

        # Fetch live prices for all instruments in ONE API call (LONG_TERM only — hourly candle is fresh in SHORT_TERM)
        if mode == StrategyMode.LONG_TERM:
            live_prices = shared_fetcher.fetch_batch_prices(sym_list)
        else:
            live_prices = {}

        # We'll allow the analyzer to use whatever history it has from previous runs or fall back
        macro_batch = {}
        pullback_batch = {}

    results = []
    data_map = {}

    def process_instrument(inst):
        sym = inst['symbol'].upper()
        t_inst = time.time()
        try:
            # Improved Crypto Detection (Whitelisted for BTC)
            is_crypto = any(sub in sym for sub in ["BTC", "CRYPTO", "BITCOIN"]) or (len(sym) > 6 and "USD" in sym)
            bench = btc_bench if is_crypto else spy_bench
            bench_exec_df = benchmarks_data.get("BTC_exec") if is_crypto else benchmarks_data.get("SPX_exec")
            
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
                sym, analysis, hist_data = future.result()
                if analysis:
                    results.append(analysis)
                    data_map[sym] = hist_data
                    # Alerts
                    if analysis.trade_signal.trade_worthy:
                        alert_key = f"{user_id}_{sym}_{analysis.trade_signal.recommendation}_{date.today()}_{mode.value}"
                        if alert_key not in SENT_ALERTS:
                            send_alerts(analysis, alert_config)
                            SENT_ALERTS.add(alert_key)
                else:
                    logger.warning(f"Analysis produced no result for {sym}")
    except Exception as e:
        logger.error(f"Parallel analysis loop failed: {e}")
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
    from .config_loader import load_config, get_instruments, save_instruments
    config = load_config(user_id=user_id)
    instruments = get_instruments(config)
    
    if len(instruments) >= 5:
        raise HTTPException(status_code=400, detail="Maximum limit of 5 instruments reached. Please remove an instrument before adding a new one.")
    
    symbol = instrument_data.get("symbol", "").upper()
    name = instrument_data.get("name", "")

    from .config_loader import ALLOWED_SYMBOLS, BENCHMARK_ONLY_SYMBOLS
    if symbol in BENCHMARK_ONLY_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"{symbol} is a benchmark used internally and cannot be added as a user instrument.")
    if symbol not in ALLOWED_SYMBOLS:
        raise HTTPException(status_code=400, detail=f"{symbol} is not a supported instrument. Allowed: {', '.join(sorted(ALLOWED_SYMBOLS))}")

    if any(i['symbol'].upper() == symbol for i in instruments):
        raise HTTPException(status_code=400, detail=f"Symbol {symbol} already exists")
    
    instruments.append({"symbol": symbol, "name": name})
    save_instruments(instruments, user_id=user_id)
    return {"message": f"Instrument {symbol} added successfully", "instruments": instruments}

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

# Handler for AWS Lambda
handler = Mangum(app)
