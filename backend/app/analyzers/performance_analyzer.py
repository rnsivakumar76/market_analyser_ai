import pandas as pd
import logging
from typing import List, Dict, Any
from .trend_analyzer import analyze_monthly_trend
from .pullback_analyzer import analyze_weekly_pullback
from .strength_analyzer import analyze_daily_strength
from .candle_analyzer import detect_candle_patterns
from .volatility_analyzer import calculate_atr
from ..signal_generator import generate_trade_signal
from ..models import Signal, PerformanceSummary, CandleAnalysis, StrategySettings

logger = logging.getLogger(__name__)

def calculate_weekly_performance(instruments: List[Dict[str, Any]], data_map: Dict[str, pd.DataFrame], params: Dict[str, Any], benchmarks: Dict[str, Signal], settings: StrategySettings = None) -> PerformanceSummary:
    """
    Calculate the theoretical PnL of all "Trade Worthy" signals that appeared in the last 7 trading days.
    """
    trades = []
    
    for inst in instruments:
        symbol = inst['symbol'].upper()
        if symbol not in data_map:
            continue
            
        df = data_map[symbol]
        if len(df) < 50: # Need enough history for indicators
            continue
            
        # Get appropriate benchmark (Whitelisted for BTC-USD)
        is_crypto = "-USD" in symbol or "BTC" in symbol
        bench_dir = benchmarks.get("BTC" if is_crypto else "SPX", Signal.NEUTRAL)
        
        # Look back up to 7 trading days
        # We start from 10 days ago to see if signals fired and reached TP/SL
        lookback_start = max(50, len(df) - 10)
        
        for idx in range(lookback_start, len(df) - 2): # Stop 2 days before today to allow for trade resolution
            window = df.iloc[idx-40:idx+1]
            current_price = window.iloc[-1]['Close']
            
            # Run the full strategy as it was
            trend = analyze_monthly_trend(window, params.get('monthly', {}))
            
            # Simple weekly approximation for performance tracking speed
            weekly_window = window.iloc[::5]
            pullback = analyze_weekly_pullback(weekly_window, current_price, params.get('weekly', {}))
            strength = analyze_daily_strength(window, params.get('daily', {}))
            candle = detect_candle_patterns(window)
            
            # Wrap candle in the pydantic model for signal generator
            candle_model = CandleAnalysis(
                pattern=candle['pattern'],
                description=candle['description'],
                is_bullish=candle.get('is_bullish')
            )
            
            signal = generate_trade_signal(
                trend=trend, 
                pullback=pullback, 
                strength=strength, 
                candle=candle_model, 
                benchmark_direction=bench_dir, 
                settings=settings
            )
            
            if signal.trade_worthy:
                # ENTRY detected at 'idx'
                # We enter on the next day's open
                entry_idx = idx + 1
                entry_price = df.iloc[entry_idx]['Open']
                atr = calculate_atr(window)
                
                if atr <= 0: continue
                
                direction = 1 if signal.recommendation == Signal.BULLISH else -1
                sl_mult = settings.atr_multiplier_sl if settings else 1.5
                tp_mult = settings.atr_multiplier_tp if settings else 3.0
                
                stop_loss = entry_price - (direction * atr * sl_mult)
                take_profit = entry_price + (direction * atr * tp_mult)
                
                # Check outcome in subsequent days (up to 5 days after entry)
                pnl = None
                for t in range(entry_idx, min(entry_idx + 6, len(df))):
                    high = df.iloc[t]['High']
                    low = df.iloc[t]['Low']
                    close = df.iloc[t]['Close']
                    
                    if direction == 1:
                        if low <= stop_loss:
                            pnl = (stop_loss - entry_price) / entry_price
                            break
                        if high >= take_profit:
                            pnl = (take_profit - entry_price) / entry_price
                            break
                    else:
                        if high >= stop_loss:
                            pnl = (entry_price - stop_loss) / entry_price
                            break
                        if low <= take_profit:
                            pnl = (entry_price - take_profit) / entry_price
                            break
                
                # If trade still open at end of window, close at current price
                if pnl is None:
                    pnl = (df.iloc[-1]['Close'] - entry_price) / entry_price * direction
                
                trades.append({
                    "symbol": symbol,
                    "pnl": pnl * 100, # Percentage
                })
                
                # Deduplicate: only take the FIRST signal per instrument in the window
                break

    # Summarize results
    total_trades = len(trades)
    if total_trades == 0:
        return PerformanceSummary(
            total_pnl_percent=0.0,
            total_trades=0,
            win_rate=0.0,
            best_trade_symbol="N/A",
            best_trade_pnl=0.0,
            worst_trade_symbol="N/A",
            worst_trade_pnl=0.0,
            description="No theoretical signals reached conviction threshold in the last 7 days."
        )

    wins = [t for t in trades if t['pnl'] > 0]
    total_pnl = sum([t['pnl'] for t in trades])
    win_rate = (len(wins) / total_trades) * 100
    
    best = max(trades, key=lambda x: x['pnl'])
    worst = min(trades, key=lambda x: x['pnl'])
    
    desc = f"Weekly Recap: The strategy identified {total_trades} high-conviction setups. "
    if total_pnl > 0:
        desc += f"Hypothetical PnL: +{total_pnl:.2f}% ✅."
    else:
        desc += f"Hypothetical PnL: {total_pnl:.2f}% ⚠️ (Wait for better market regimes)."

    return PerformanceSummary(
        total_pnl_percent=round(total_pnl, 2),
        total_trades=total_trades,
        win_rate=round(win_rate, 1),
        best_trade_symbol=best['symbol'],
        best_trade_pnl=round(best['pnl'], 2),
        worst_trade_symbol=worst['symbol'],
        worst_trade_pnl=round(worst['pnl'], 2),
        description=desc
    )
