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
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
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
    mae_trades = []  # Max Adverse Excursion per winning trade

    # Step through data (starting after we have enough for MAs)
    # To keep it fast, we'll only check the last 400 trading days
    start_idx = max(100, len(daily_data) - 400)
    
    idx = start_idx
    while idx < len(daily_data) - 10:
        # Window of data UP TO current index
        window = daily_data.iloc[max(0, idx-150):idx+1]
        
        # Current status
        current_price = daily_data.iloc[idx]['Close']
        
        # Simplified components for historical simulation
        trend = analyze_monthly_trend(window, params.get('monthly', {}))
        
        # For backtest, we simulate weekly by resampling if we have enough data
        # or just use a longer lookback on daily
        pullback = analyze_weekly_pullback(window, current_price, params.get('weekly', {}))
        strength = analyze_daily_strength(window, params.get('daily', {}))
        
        # Simplified triggers for backtest to get statistical sample
        # We assume if the core signal is strong, a trader would find an entry trigger
        # so we skip the strict candlestick pattern matching here
        candle = CandleAnalysis(pattern="backtest_sim", description="Simulated", is_bullish=(trend.direction == Signal.BULLISH))
        
        signal = generate_trade_signal(
            trend, pullback, strength, candle, 
            benchmark_direction=Signal.BULLISH, # Assume healthy market for backtest
            settings=settings,
            current_price=current_price
        )
        
        if signal.trade_worthy or (signal.score >= (settings.conviction_threshold - 10 if settings else 60)):
            # Enter trade!
            try:
                entry_price = daily_data.iloc[idx+1]['Open']
                atr = calculate_atr(window)
                
                if atr > 0:
                    direction = 1 if signal.recommendation == Signal.BULLISH else -1
                    # Slightly tighter SL/TP for more realistic "Tactical" performance
                    sl_mult = settings.atr_multiplier_sl if settings else 1.5
                    tp_mult = settings.atr_multiplier_tp if settings else 3.0
                    
                    stop_loss = entry_price - (direction * atr * sl_mult)
                    take_profit = entry_price + (direction * atr * tp_mult)
                    
                    # Monitor trade for up to 20 bars
                    won = None
                    pnl = 0.0
                    worst_adverse = 0.0  # MAE tracking
                    for t in range(idx + 1, min(idx + 21, len(daily_data))):
                        bar = daily_data.iloc[t]
                        if direction == 1:
                            adverse = (entry_price - bar['Low']) / entry_price
                            worst_adverse = max(worst_adverse, adverse)
                            if bar['Low'] <= stop_loss:
                                won = False
                                pnl = (stop_loss - entry_price) / entry_price
                                break
                            if bar['High'] >= take_profit:
                                won = True
                                pnl = (take_profit - entry_price) / entry_price
                                break
                        else:
                            adverse = (bar['High'] - entry_price) / entry_price
                            worst_adverse = max(worst_adverse, adverse)
                            if bar['High'] >= stop_loss:
                                won = False
                                pnl = (entry_price - stop_loss) / entry_price
                                break
                            if bar['Low'] <= take_profit:
                                won = True
                                pnl = (entry_price - take_profit) / entry_price
                                break

                    if won is not None:
                        trades.append(pnl)
                        if won:
                            mae_trades.append(worst_adverse)
                        idx += 5  # Move forward
                    else:
                        # Time exit (small gain or loss)
                        idx += 1
                else:
                    idx += 1
            except:
                idx += 1
        else:
            idx += 1

    # Calculate stats
    total = len(trades)
    if total == 0:
        results = BacktestAnalysis(
            win_rate=0.0, total_trades=0, profit_factor=0.0,
            avg_win=0.0, avg_loss=0.0, sample_size=0,
            description="Historical Edge: No high-probability setups identified in the 1-year window."
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

        # Expectancy per trade (as % of position)
        win_rate_dec = win_rate / 100
        loss_rate_dec = 1 - win_rate_dec
        expectancy = round((win_rate_dec * avg_win) - (loss_rate_dec * avg_loss), 3)

        # Sharpe Ratio (annualised, assumes ~252 trades/year scaling)
        trade_arr = np.array(trades)
        sharpe = 0.0
        if trade_arr.std() > 0:
            sharpe = round(float((trade_arr.mean() / trade_arr.std()) * np.sqrt(252)), 2)

        # Max Drawdown via equity curve
        equity = np.cumprod(1 + trade_arr)
        peak = np.maximum.accumulate(equity)
        drawdowns = (equity - peak) / peak
        max_dd = round(float(drawdowns.min()) * 100, 2)

        # Max consecutive losses
        max_streak = 0
        cur_streak = 0
        for t in trades:
            if t <= 0:
                cur_streak += 1
                max_streak = max(max_streak, cur_streak)
            else:
                cur_streak = 0

        # MAE: tracked per trade during backtest (mae_trades list from loop above)
        avg_mae = round(float(np.mean(mae_trades)) * 100, 2) if mae_trades else 0.0

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
            description=desc,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd,
            max_consecutive_losses=max_streak,
            max_adverse_excursion_pct=avg_mae,
            sample_size=total,
            expectancy=expectancy
        )

    # Save to cache
    cache[cache_key] = results.dict()
    _save_cache(cache)
    
    return results
