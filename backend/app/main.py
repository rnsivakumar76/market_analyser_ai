from fastapi import FastAPI, HTTPException
from mangum import Mangum
from datetime import datetime, date
from typing import List, Dict, Any
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config_loader import (
    load_config, get_instruments, get_analysis_params, 
    save_instruments, get_alert_config, get_strategy_config, save_strategy_config
)
from .notifier import send_alerts
from .data_fetcher import fetch_historical_data, fetch_weekly_data, get_current_price, _get_yf_symbol
from .analyzers import (
    analyze_monthly_trend, 
    analyze_weekly_pullback, 
    analyze_daily_strength,
    analyze_market_phase,
    analyze_volatility_and_risk,
    analyze_fundamentals,
    get_backtest_results,
    detect_candle_patterns,
    calculate_weekly_performance,
    calculate_correlations,
    apply_position_sizing
)
from .signal_generator import generate_trade_signal
from .models import (
    InstrumentAnalysis, AnalysisResponse, InstrumentConfig, 
    Signal, StrategySettings
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Market Analyzer API",
    description="Analyze instruments for trading opportunities",
    version="1.0.0"
)

# No CORS middleware here - handled by AWS API Gateway for better performance and to avoid double-header issues.


def analyze_instrument(symbol: str, name: str, params: dict, benchmark_direction: Signal = Signal.NEUTRAL, strategy_settings: StrategySettings = None) -> InstrumentAnalysis:
    """Perform complete analysis on a single instrument."""
    logger.info(f"Analyzing {symbol}...")
    
    # Fetch data
    # Fetch data - increased days to 500 to support historical backtest
    daily_data = fetch_historical_data(symbol, days=500)
    weekly_data = fetch_weekly_data(symbol, weeks=12)
    current_price = get_current_price(symbol)
    
    # Run analyses
    monthly_params = params.get('monthly', {})
    weekly_params = params.get('weekly', {})
    daily_params = params.get('daily', {})
    
    trend = analyze_monthly_trend(daily_data, monthly_params)
    pullback = analyze_weekly_pullback(weekly_data, current_price, weekly_params)
    strength = analyze_daily_strength(daily_data, daily_params)
    phase = analyze_market_phase(daily_data, daily_params)
    
    # 3. Price Action Trigger (Detection of Hammers/Engulfing candles)
    candle_res = detect_candle_patterns(daily_data)
    
    # Generate trade signal
    trade_signal = generate_trade_signal(
        trend, pullback, strength, 
        candle_res, benchmark_direction,
        settings=strategy_settings
    )
    
    # Calculate stop loss, take profit and ATR based on trade signal
    volatility = analyze_volatility_and_risk(
        daily_data, 
        current_price, 
        trade_signal.recommendation.value
    )
    
    # Check Fundamental Macro events (Earnings & Economic Calendar)
    yf_symbol = _get_yf_symbol(symbol)
    fundamentals = analyze_fundamentals(symbol, yf_symbol)
    
    # Run Backtest (Checks historical success rate for this strategy on this symbol)
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

async def run_scheduled_analysis():
    """Background task to analyze all instruments concurrently for speed on AWS Lambda."""
    try:
        logger.info("Running parallel market scan...")
        config = load_config()
        instruments = get_instruments(config)
        params = get_analysis_params(config)
        alert_config = get_alert_config(config)
        strategy_settings_data = get_strategy_config(config)
        strategy_settings = StrategySettings(**strategy_settings_data)
        
        # Benchmark data fetching (Parallel)
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

        spy_data = benchmarks_data.get("SPX")
        btc_data = benchmarks_data.get("BTC-USD")
        
        spy_bench = Signal.NEUTRAL
        btc_bench = Signal.NEUTRAL
        
        if spy_data is not None and not spy_data.empty:
            spy_bench = analyze_monthly_trend(spy_data, params.get('monthly', {})).direction
        if btc_data is not None and not btc_data.empty:
            btc_bench = analyze_monthly_trend(btc_data, params.get('monthly', {})).direction
            
        benchmarks = {"SPX": spy_bench, "BTC-USD": btc_bench}

        results: List[InstrumentAnalysis] = []
        data_map = {}

        def process_instrument(inst):
            sym = inst['symbol'].upper()
            try:
                bench = btc_bench if ("-USD" in sym or "BTC" in sym or "ETH" in sym) else spy_bench
                analysis = analyze_instrument(sym, inst['name'], params, bench, strategy_settings)
                hist_data = fetch_historical_data(sym, days=60)
                return sym, analysis, hist_data
            except Exception as e:
                logger.error(f"Error analyzing {sym}: {e}")
                return sym, None, None

        # Process all instruments in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_inst = {executor.submit(process_instrument, inst): inst for inst in instruments}
            for future in as_completed(future_to_inst):
                sym, analysis, hist_data = future.result()
                if analysis:
                    results.append(analysis)
                    data_map[sym] = hist_data
                    
                    # Notification Logic
                    if analysis.trade_signal.trade_worthy:
                        alert_key = f"{sym}_{analysis.trade_signal.recommendation}_{date.today()}"
                        if alert_key not in SENT_ALERTS:
                            send_alerts(analysis, alert_config)
                            SENT_ALERTS.add(alert_key)

        # Calculate summaries (Synchronous)
        perf_summary = calculate_weekly_performance(instruments, data_map, params, benchmarks, strategy_settings)
        correlation_results = calculate_correlations(data_map)
        results = apply_position_sizing(results, correlation_results, strategy_settings)
        
        return results, perf_summary, correlation_results
    except Exception as e:
        logger.error(f"Concurrent analysis failed: {str(e)}")
        return [], None, None

# Scheduler removed for AWS Lambda (handled by EventBridge)

@app.get("/api/analyze", response_model=AnalysisResponse)
async def analyze_all():
    """Analyze all configured instruments."""
    results, perf, corr = await run_scheduled_analysis()
    return AnalysisResponse(
        analysis_timestamp=datetime.now().isoformat(),
        instruments=results,
        weekly_performance=perf,
        correlation_data=corr
    )


@app.get("/api/analyze/{symbol}", response_model=InstrumentAnalysis)
async def analyze_single(symbol: str):
    """Analyze a single instrument by symbol."""
    try:
        config = load_config()
        params = get_analysis_params(config)
        instruments = get_instruments(config)
        strategy_settings = StrategySettings(**get_strategy_config(config))
        
        # Find instrument name
        name = symbol
        for inst in instruments:
            if inst['symbol'].upper() == symbol.upper():
                name = inst['name']
                break
        
        analysis = analyze_instrument(symbol.upper(), name, params, strategy_settings=strategy_settings)
        return analysis
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/instruments")
async def list_instruments():
    """List all configured instruments."""
    config = load_config()
    return {"instruments": get_instruments(config)}


@app.post("/api/instruments")
async def add_instrument(instrument: InstrumentConfig):
    """Add a new instrument to the configuration."""
    config = load_config()
    instruments = get_instruments(config)
    
    # Check if symbol already exists
    if any(i['symbol'].upper() == instrument.symbol.upper() for i in instruments):
        raise HTTPException(status_code=400, detail=f"Symbol {instrument.symbol} already exists")
    
    # Simple validation using yfinance
    try:
        yf_sym = _get_yf_symbol(instrument.symbol)
        import yfinance as yf
        ticker = yf.Ticker(yf_sym)
        # Try to get the current price as a basic sanity check
        data = ticker.history(period="1d")
        if data.empty:
            raise ValueError(f"No market data found for {instrument.symbol}")
    except Exception as e:
        logger.error(f"Validation failed for {instrument.symbol}: {e}")
        raise HTTPException(status_code=400, detail=f"Could not validate symbol {instrument.symbol}: {str(e)}")

    instruments.append({"symbol": instrument.symbol.upper(), "name": instrument.name})
    save_instruments(instruments)
    return {"message": f"Instrument {instrument.symbol} added successfully", "instruments": instruments}


@app.delete("/api/instruments/{symbol}")
async def delete_instrument(symbol: str):
    """Remove an instrument from the configuration."""
    config = load_config()
    instruments = get_instruments(config)
    
    # Filter out the symbol
    new_instruments = [i for i in instruments if i['symbol'].upper() != symbol.upper()]
    
    if len(new_instruments) == len(instruments):
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    save_instruments(new_instruments)
    return {"message": f"Instrument {symbol} removed successfully", "instruments": new_instruments}


@app.get("/api/settings", response_model=StrategySettings)
async def get_settings():
    """Retrieve current strategy settings."""
    config = load_config()
    return get_strategy_config(config)


@app.post("/api/settings")
async def update_settings(settings: StrategySettings):
    """Update strategy settings."""
    save_strategy_config(settings.dict())
    return {"message": "Strategy settings updated successfully"}


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Handler for AWS Lambda
handler = Mangum(app)
