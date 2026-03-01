import pandas as pd
import numpy as np
from typing import List, Optional
import logging

from ..models import LiquidityMap, LiquidityLevel

logger = logging.getLogger(__name__)

_TOP_N = 3  # top 3 levels per side


def _find_swing_highs(highs: pd.Series, lookback: int = 5) -> List[float]:
    """Identify swing high levels (local maxima)."""
    levels = []
    arr = highs.values
    for i in range(lookback, len(arr) - lookback):
        window = arr[i - lookback: i + lookback + 1]
        if arr[i] == window.max():
            levels.append(float(arr[i]))
    return levels


def _find_swing_lows(lows: pd.Series, lookback: int = 5) -> List[float]:
    """Identify swing low levels (local minima)."""
    levels = []
    arr = lows.values
    for i in range(lookback, len(arr) - lookback):
        window = arr[i - lookback: i + lookback + 1]
        if arr[i] == window.min():
            levels.append(float(arr[i]))
    return levels


def _cluster_levels(levels: List[float], tolerance_pct: float = 0.005) -> List[float]:
    """Merge levels that are within tolerance_pct of each other."""
    if not levels:
        return []
    levels = sorted(levels)
    clusters = []
    current = [levels[0]]
    for lvl in levels[1:]:
        if (lvl - current[-1]) / current[-1] <= tolerance_pct:
            current.append(lvl)
        else:
            clusters.append(float(np.mean(current)))
            current = [lvl]
    clusters.append(float(np.mean(current)))
    return clusters


def calculate_liquidity_map(
    df: pd.DataFrame,
    current_price: float
) -> Optional[LiquidityMap]:
    """
    Build a simple liquidity map from swing highs/lows.
    Returns top 3 resistance levels above price and top 3 support levels below.
    """
    try:
        if df is None or len(df) < 30:
            return None

        data = df.tail(200).copy()
        lookback = 5

        swing_highs = _find_swing_highs(data['High'], lookback)
        swing_lows = _find_swing_lows(data['Low'], lookback)

        # Also include round-number levels (psychological)
        price_range = data['High'].max() - data['Low'].min()
        step = 10 ** (len(str(int(current_price))) - 2)
        round_low = int(data['Low'].min() / step) * step
        round_high = int(data['High'].max() / step + 1) * step
        round_numbers = [round_low + i * step for i in range(int((round_high - round_low) / step) + 1)]

        all_resistance = swing_highs + [r for r in round_numbers if r > current_price]
        all_support = swing_lows + [r for r in round_numbers if r < current_price]

        resistance_clustered = _cluster_levels([r for r in all_resistance if r > current_price])
        support_clustered = _cluster_levels(sorted([s for s in all_support if s < current_price], reverse=True))

        def build_levels(prices: List[float], level_type: str) -> List[LiquidityLevel]:
            result = []
            for p in prices[:_TOP_N]:
                dist_pct = abs(p - current_price) / current_price * 100
                # Estimate strength by how many swings cluster here
                touches = sum(
                    1 for raw in (swing_highs if level_type == "resistance" else swing_lows)
                    if abs(raw - p) / p <= 0.008
                )
                strength = "strong" if touches >= 3 else "moderate" if touches >= 2 else "weak"
                result.append(LiquidityLevel(
                    price=round(p, 4),
                    distance_pct=round(dist_pct, 2),
                    level_type=level_type,
                    strength=strength,
                    touches=touches
                ))
            return result

        resistance_levels = build_levels(resistance_clustered, "resistance")
        support_levels = build_levels(support_clustered, "support")

        # Nearest levels for quick description
        nearest_res = resistance_levels[0].price if resistance_levels else None
        nearest_sup = support_levels[0].price if support_levels else None

        parts = []
        if nearest_res:
            parts.append(f"Nearest resistance: ${nearest_res:.2f} ({resistance_levels[0].distance_pct:.1f}% away)")
        if nearest_sup:
            parts.append(f"Nearest support: ${nearest_sup:.2f} ({support_levels[0].distance_pct:.1f}% below)")
        interpretation = " | ".join(parts) if parts else "Insufficient price history for liquidity map."

        return LiquidityMap(
            resistance_levels=resistance_levels,
            support_levels=support_levels,
            interpretation=interpretation
        )

    except Exception as e:
        logger.error(f"Liquidity map calculation failed: {e}")
        return None
