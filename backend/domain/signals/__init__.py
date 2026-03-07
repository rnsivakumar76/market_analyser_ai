"""
Trade signal computation — scoring, hard filters, conflict detection.

All functions operate on primitive types or lightweight dataclasses.
No pandas DataFrames, no Pydantic models, no FastAPI.
"""

from .scoring_engine import (
    compute_trend_score,
    compute_pullback_score,
    compute_strength_score,
    compute_composite_score,
    ScoreComponents,
)
from .filter_engine import (
    FilterResult,
    apply_adx_filter,
    apply_benchmark_filter,
    apply_candle_filter,
    apply_macro_shield,
    apply_relative_strength_filter,
    apply_all_hard_filters,
)
from .conflict_detector import (
    ConflictResult,
    detect_adx_direction_mismatch,
    detect_mtf_disagreement,
    detect_signal_conflict,
)

__all__ = [
    "compute_trend_score",
    "compute_pullback_score",
    "compute_strength_score",
    "compute_composite_score",
    "ScoreComponents",
    "FilterResult",
    "apply_adx_filter",
    "apply_benchmark_filter",
    "apply_candle_filter",
    "apply_macro_shield",
    "apply_relative_strength_filter",
    "apply_all_hard_filters",
    "ConflictResult",
    "detect_adx_direction_mismatch",
    "detect_mtf_disagreement",
    "detect_signal_conflict",
]
