from fastapi import FastAPI, HTTPException, Depends
from starlette.middleware.sessions import SessionMiddleware
from mangum import Mangum
from datetime import datetime, date
from typing import List, Dict, Any
import logging
import os

# Import auth dependencies - these are light
from .auth import get_current_user
from .oauth import router as auth_router

# Base logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Market Analyzer API",
    description="Analyze instruments for trading opportunities",
    version="1.0.0"
)

# CORS Middleware - essential for browser-to-lambda cross-domain calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Required for Authlib OAuth state storage
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "super-secret-session-key"))

# Include Auth routes at top level - these are fast enough
app.include_router(auth_router, prefix="/api")

# Lazy analysis helper to keep imports deferred
def analyze_instrument_lazy(symbol: str, name: str, params: dict, benchmark_direction: Any = None, strategy_settings: Any = None) -> Any:
    """Perform complete analysis on a single instrument with lazy imports."""
    from .data_fetcher import fetch_historical_data, fetch_weekly_data, get_current_price, _get_yf_symbol
    from .analyzers import (
        analyze_monthly_trend, analyze_weekly_pullback, analyze_daily_strength,
        analyze_market_phase, analyze_volatility_and_risk, analyze_fundamentals,
        get_backtest_results, detect_candle_patterns
    )
    from .signal_generator import generate_trade_signal
    from .models import InstrumentAnalysis
    
    logger.info(f"Analyzing {symbol}...")
    
    # Fetch data
    daily_data = fetch_historical_data(symbol, days=500)
    weekly_data = fetch_weekly_data(symbol, weeks=12)
    current_price = get_current_price(symbol)
    
    trend = analyze_monthly_trend(daily_data, params.get('monthly', {}))
    pullback = analyze_weekly_pullback(weekly_data, current_price, params.get('weekly', {}))
    strength = analyze_daily_strength(daily_data, params.get('daily', {}))
    phase = analyze_market_phase(daily_data, params.get('daily', {}))
    candle_res = detect_candle_patterns(daily_data)
    
    trade_signal = generate_trade_signal(
        trend, pullback, strength, 
        candle_res, benchmark_direction,
        settings=strategy_settings
    )
    
    volatility = analyze_volatility_and_risk(daily_data, current_price, trade_signal.recommendation.value)
    fundamentals = analyze_fundamentals(symbol, _get_yf_symbol(symbol))
    backtest = get_backtest_results(symbol, daily_data, params)
    
    return InstrumentAnalysis(
        symbol=symbol,
        name=name,
        current_price=round(current_price, 2),
        analysis_date=date.today(),
        monthly_trend=trend,
        weekly_pullback=pullback,
        daily_strength=strength,
        market_phase=phase,
        volatility_risk=volatility,
        fundamentals=fundamentals,
        backtest_results=backtest,
        candle_patterns=candle_res,
        benchmark_direction=benchmark_direction,
        trade_signal=trade_signal
    )

@app.get("/")
async def root():
    return {"message": "Market Analyzer API", "status": "running"}

# In-memory store for sent alerts
SENT_ALERTS = set()

async def run_scheduled_analysis(user_id: str = "global_default"):
    from .config_loader import load_config, get_instruments, get_analysis_params, get_alert_config, get_strategy_config
    from .models import StrategySettings, Signal
    from .data_fetcher import fetch_historical_data
    from .analyzers import analyze_monthly_trend, calculate_weekly_performance, calculate_correlations, apply_position_sizing
    from .notifier import send_alerts
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    logger.info(f"Running parallel market scan for user: {user_id}...")
    config = load_config(user_id=user_id)
    instruments = get_instruments(config)
    params = get_analysis_params(config)
    alert_config = get_alert_config(config)
    strategy_settings = StrategySettings(**get_strategy_config(config))
    
    # Parallel Fetch
    benchmarks_data = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(fetch_historical_data, "SPX", days=60): "SPX",
            executor.submit(fetch_historical_data, "BTC-USD", days=60): "BTC-USD"
        }
        for future in as_completed(futures):
            sym = futures[future]
            try:
                benchmarks_data[sym] = future.result()
            except Exception as e:
                logger.error(f"Failed to fetch benchmark {sym}: {e}")
                benchmarks_data[sym] = None

    spy_bench = Signal.NEUTRAL
    btc_bench = Signal.NEUTRAL
    if benchmarks_data.get("SPX") is not None and not benchmarks_data["SPX"].empty:
        spy_bench = analyze_monthly_trend(benchmarks_data["SPX"], params.get('monthly', {})).direction
    if benchmarks_data.get("BTC-USD") is not None and not benchmarks_data["BTC-USD"].empty:
        btc_bench = analyze_monthly_trend(benchmarks_data["BTC-USD"], params.get('monthly', {})).direction
            
    results = []
    data_map = {}

    def process_instrument(inst):
        sym = inst['symbol'].upper()
        try:
            bench = btc_bench if ("-USD" in sym or "BTC" in sym or "ETH" in sym) else spy_bench
            analysis = analyze_instrument_lazy(sym, inst['name'], params, bench, strategy_settings)
            hist_data = fetch_historical_data(sym, days=60)
            return sym, analysis, hist_data
        except Exception as e:
            logger.error(f"Error analyzing {sym}: {e}")
            return sym, None, None

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_inst = {executor.submit(process_instrument, inst): inst for inst in instruments}
        for future in as_completed(future_to_inst):
            sym, analysis, hist_data = future.result()
            if analysis:
                results.append(analysis)
                data_map[sym] = hist_data
                if analysis.trade_signal.trade_worthy:
                    alert_key = f"{user_id}_{sym}_{analysis.trade_signal.recommendation}_{date.today()}"
                    if alert_key not in SENT_ALERTS:
                        send_alerts(analysis, alert_config)
                        SENT_ALERTS.add(alert_key)

    perf_summary = calculate_weekly_performance(instruments, data_map, params, {"SPX": spy_bench, "BTC-USD": btc_bench}, strategy_settings)
    correlation_results = calculate_correlations(data_map)
    results = apply_position_sizing(results, correlation_results, strategy_settings)
    
    return results, perf_summary, correlation_results

@app.get("/api/analyze")
async def analyze_all(user_id: str = Depends(get_current_user)):
    from .models import AnalysisResponse
    results, perf, corr = await run_scheduled_analysis(user_id=user_id)
    return AnalysisResponse(
        analysis_timestamp=datetime.now().isoformat(),
        instruments=results,
        weekly_performance=perf,
        correlation_data=corr
    )

@app.get("/api/analyze/{symbol}")
async def analyze_single(symbol: str, user_id: str = Depends(get_current_user)):
    from .config_loader import load_config, get_instruments, get_analysis_params, get_strategy_config
    from .models import StrategySettings
    
    config = load_config(user_id=user_id)
    params = get_analysis_params(config)
    instruments = get_instruments(config)
    strategy_settings = StrategySettings(**get_strategy_config(config))
    
    name = symbol
    for inst in instruments:
        if inst['symbol'].upper() == symbol.upper():
            name = inst['name']
            break
            
    return analyze_instrument_lazy(symbol.upper(), name, params, strategy_settings=strategy_settings)

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
    
    symbol = instrument_data.get("symbol", "").upper()
    name = instrument_data.get("name", "")
    
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
    from .config_loader import load_config, get_strategy_config
    config = load_config(user_id=user_id)
    return get_strategy_config(config)

@app.post("/api/settings")
async def update_settings(settings: Dict[str, Any], user_id: str = Depends(get_current_user)):
    from .config_loader import save_strategy_config
    save_strategy_config(settings, user_id=user_id)
    return {"message": "Strategy settings updated successfully"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Handler for AWS Lambda
handler = Mangum(app)
