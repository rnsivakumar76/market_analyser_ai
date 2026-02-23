import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..models import BacktestAnalysis, Signal, CandleAnalysis, StrategySettings
from .trend_analyzer import analyze_monthly_trend
from .pullback_analyzer import analyze_weekly_pullback
from .strength_analyzer import analyze_daily_strength
from .volatility_analyzer import calculate_atr
from ..signal_generator import generate_trade_signal

import os

logger = logging.getLogger(__name__)

# Lambda specific cache location
if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
    CACHE_DIR = Path("/tmp") / "cache"
else:
    CACHE_DIR = Path(__file__).parent.parent.parent / "cache"

CACHE_FILE = CACHE_DIR / "backtest_cache.json"

def _load_cache():
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True)
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_cache(cache):
    try:
        if not CACHE_DIR.exists():
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        logger.warning(f"Could not save backtest cache: {e}")

def get_backtest_results(symbol: str, daily_data: pd.DataFrame, params: Dict[str, Any], settings: StrategySettings = None) -> BacktestAnalysis:
    """Run a historical backtest for a symbol or return cached results."""
    cache = _load_cache()
    
    # Simple cache key: symbol + day + settings hash
    last_date = daily_data.index[-1].strftime('%Y-%m-%d')
    settings_key = f"{settings.conviction_threshold}_{settings.adx_threshold}" if settings else "default"
    cache_key = f"{symbol}_{last_date}_{settings_key}"
    
    if cache_key in cache:
        logger.info(f"Using cached backtest results for {symbol}")
        return BacktestAnalysis(**cache[cache_key])

    logger.info(f"Running new backtest for {symbol}...")
    
    # We need at least 100 days of data to start a window (for MAs and ATR)
    if len(daily_data) < 150:
        return BacktestAnalysis(
            win_rate=0.0, total_trades=0, profit_factor=0.0, 
            avg_win=0.0, avg_loss=0.0, 
            description="Insufficient historical data for backtesting."
        )

    trades = []
    
    # Step through data (starting after we have enough for MAs)
    # To keep it fast, we'll only check the last 250 trading days (approx 1 year)
    start_idx = max(100, len(daily_data) - 400)
    
    # For weekly pullback, we need a separate "weekly" frame or we simulate it
    # To keep it simple, we'll approximate weekly data from the daily set in the loop
    
    idx = start_idx
    while idx < len(daily_data) - 10: # leave room to see trade outcome
        # Window of data UP TO current index
        window = daily_data.iloc[idx-100:idx+1]
        
        # Current status
        current_price = daily_data.iloc[idx]['Close']
        
        # Generate signal (simplified for speed in backtest)
        trend = analyze_monthly_trend(window, params.get('monthly', {}))
        
        # Approx weekly by taking every 5th day of the current window? 
        # Or just a simplified version
        weekly_window = window.iloc[::5] # crude weekly
        pullback = analyze_weekly_pullback(weekly_window, current_price, params.get('weekly', {}))
        
        strength = analyze_daily_strength(window, params.get('daily', {}))
        
        # In backtest, we skip benchmark and specific trigger filtering to keep it fast
        # but we must provide the objects
        candle = CandleAnalysis(pattern="none", description="Backtest skip", is_bullish=True) 
        if signal_direction := trend.direction:
             # Force candle to match trend so trigger doesn't block backtest
             candle.is_bullish = (signal_direction == Signal.BULLISH)

        signal = generate_trade_signal(trend, pullback, strength, candle, benchmark_direction=Signal.BULLISH, settings=settings)
        
        if signal.trade_worthy:
            # Enter trade!
            entry_price = daily_data.iloc[idx+1]['Open'] # Enter on next day's open
            atr = calculate_atr(window)
            
            if atr > 0:
                direction = 1 if signal.recommendation == Signal.BULLISH else -1
                stop_loss = entry_price - (direction * atr * 1.5)
                take_profit = entry_price + (direction * atr * 3.0)
                
                # Monitor trade
                won = None
                for t in range(idx + 1, min(idx + 30, len(daily_data))): # Max holding period 30 days
                    high = daily_data.iloc[t]['High']
                    low = daily_data.iloc[t]['Low']
                    
                    if direction == 1:
                        if low <= stop_loss:
                            won = False
                            pnl = (stop_loss - entry_price) / entry_price
                            break
                        if high >= take_profit:
                            won = True
                            pnl = (take_profit - entry_price) / entry_price
                            break
                    else:
                        if high >= stop_loss:
                            won = False
                            pnl = (entry_price - stop_loss) / entry_price
                            break
                        if low <= take_profit:
                            won = True
                            pnl = (entry_price - take_profit) / entry_price
                            break
                
                if won is not None:
                    trades.append(pnl)
                    # Fast forward index beyond trade? Let's stay simple: +1
                    idx += 5 # Skip a few days to avoid overlapping identical signals
                else:
                    idx += 1
            else:
                idx += 1
        else:
            idx += 1

    # Calculate stats
    total = len(trades)
    if total == 0:
        results = BacktestAnalysis(
            win_rate=0.0, total_trades=0, profit_factor=0.0, 
            avg_win=0.0, avg_loss=0.0, 
            description="No trade setups found in the historical backtest window."
        )
    else:
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = (len(wins) / total) * 100
        
        sum_wins = sum(wins)
        sum_losses = abs(sum(losses))
        profit_factor = sum_wins / sum_losses if sum_losses > 0 else 99.9
        
        avg_win = (sum_wins / len(wins) * 100) if wins else 0
        avg_loss = (sum_losses / len(losses) * 100) if losses else 0
        
        desc = f"Historical Performance (1yr): {win_rate:.1f}% win rate over {total} trades. "
        if win_rate < 45:
            desc += "⚠️ Caution: Low historical success for this strategy/asset combo."
        else:
            desc += "✅ Solid historical performance for this setup."

        results = BacktestAnalysis(
            win_rate=round(win_rate, 1),
            total_trades=total,
            profit_factor=round(profit_factor, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            description=desc
        )

    # Save to cache
    cache[cache_key] = results.dict()
    _save_cache(cache)
    
    return results
