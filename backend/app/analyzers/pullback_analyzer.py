import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from ..models import PullbackAnalysis
from domain.levels.support_resistance import find_swing_lows, nearest_support_below


def find_recent_high(data: pd.DataFrame) -> float:
    """Find the recent swing high."""
    return float(data['High'].max())


def analyze_weekly_pullback(
    weekly_data: pd.DataFrame,
    current_price: float,
    params: Dict[str, Any]
) -> PullbackAnalysis:
    """
    Analyze weekly pullback patterns.
    
    Looks for:
    1. Price has pulled back from recent high
    2. Price is near a support level
    """
    pullback_threshold = params.get('pullback_threshold', 0.03)
    support_tolerance = params.get('support_tolerance', 0.02)
    
    if len(weekly_data) < 2:
        return PullbackAnalysis(
            detected=False,
            pullback_percent=0.0,
            near_support=False,
            support_level=None,
            description="Insufficient data for pullback analysis"
        )
    
    recent_high = find_recent_high(weekly_data)
    pullback_percent = (recent_high - current_price) / recent_high

    # Find support levels using domain layer (SSOT)
    support_levels = find_swing_lows(weekly_data['Low'].tolist(), lookback=1)
    nearest_support, near_support = nearest_support_below(
        current_price,
        support_levels,
        tolerance_pct=support_tolerance,
    )
    
    # Determine if pullback is detected
    pullback_detected = pullback_percent >= pullback_threshold
    
    if pullback_detected and near_support:
        description = f"Pullback of {pullback_percent*100:.1f}% from high ({recent_high:.2f}), near support at {nearest_support:.2f}"
    elif pullback_detected:
        description = f"Pullback of {pullback_percent*100:.1f}% from high ({recent_high:.2f}), not yet at support"
    else:
        description = f"No significant pullback ({pullback_percent*100:.1f}% from high)"
    
    return PullbackAnalysis(
        detected=pullback_detected,
        pullback_percent=float(round(pullback_percent * 100, 2)),
        near_support=bool(near_support),
        support_level=float(round(nearest_support, 2)) if nearest_support else None,
        description=description
    )
