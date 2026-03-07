import pandas as pd
import numpy as np
from app.models import RelativeStrengthAnalysis

def analyze_relative_strength(
    symbol_data: pd.DataFrame,
    benchmark_data: pd.DataFrame,
    symbol: str,
    benchmark_symbol: str,
    lookback_periods: int = 20
) -> RelativeStrengthAnalysis:
    """
    Compare the returns of the symbol against a benchmark over a specific period.
    This identifies if the asset has 'Alpha' (outperformance).
    """
    try:
        if symbol_data.empty or benchmark_data.empty:
            raise ValueError("Empty data provided for RS analysis")

        # Ensure we are looking at the same date range and frequency
        # We use 'Close' prices for return calculation
        symbol_closes = symbol_data['Close'].sort_index()
        bench_closes = benchmark_data['Close'].sort_index()

        # Guard: remove duplicate timestamps before alignment (causes reindex error otherwise)
        if symbol_closes.index.duplicated().any():
            symbol_closes = symbol_closes[~symbol_closes.index.duplicated(keep='last')]
        if bench_closes.index.duplicated().any():
            bench_closes = bench_closes[~bench_closes.index.duplicated(keep='last')]

        # Reindex to match dates if there's a slight mismatch (e.g. crypto vs stocks)
        combined = pd.DataFrame({
            'symbol': symbol_closes,
            'bench': bench_closes
        }).ffill().dropna()

        if len(combined) < lookback_periods:
            return RelativeStrengthAnalysis(
                is_outperforming=False,
                symbol_return=0.0,
                benchmark_return=0.0,
                alpha=0.0,
                label="Neutral",
                description="Insufficient data for Relative Strength (Alpha) calculation."
            )

        # Calculate returns over the lookback period
        # (Current Price / Price X periods ago) - 1
        current_idx = -1
        start_idx = -lookback_periods

        symbol_start = float(combined['symbol'].iloc[start_idx])
        symbol_end = float(combined['symbol'].iloc[current_idx])
        symbol_return = float(((symbol_end / symbol_start) - 1) * 100)

        bench_start = float(combined['bench'].iloc[start_idx])
        bench_end = float(combined['bench'].iloc[current_idx])
        bench_return = float(((bench_end / bench_start) - 1) * 100)

        alpha = float(symbol_return - bench_return)
        is_outperforming = bool(alpha > 0)

        if alpha > 5.0:
            label = "Leader"
            desc = f"Strong Alpha: {symbol} is outperforming {benchmark_symbol} by {alpha:.2f}% over the last {lookback_periods} bars. This is a Market Leader."
        elif alpha > 0:
            label = "Neutral+"
            desc = f"Moderate Strength: {symbol} is slightly outperforming {benchmark_symbol} by {alpha:.2f}%."
        elif alpha < -5.0:
            label = "Laggard"
            desc = f"Weakness: {symbol} is significantly underperforming {benchmark_symbol} by {abs(alpha):.2f}%. Avoid or wait for leadership."
        else:
            label = "Neutral-"
            desc = f"Neutral: {symbol} is performing similarly to {benchmark_symbol} ({alpha:.2f}% diff)."

        return RelativeStrengthAnalysis(
            is_outperforming=is_outperforming,
            symbol_return=round(symbol_return, 2),
            benchmark_return=round(bench_return, 2),
            alpha=round(alpha, 2),
            label=label,
            description=desc
        )

    except Exception as e:
        return RelativeStrengthAnalysis(
            is_outperforming=False,
            symbol_return=0.0,
            benchmark_return=0.0,
            alpha=0.0,
            label="Neutral",
            description=f"Relative Strength calculation error: {str(e)}"
        )
