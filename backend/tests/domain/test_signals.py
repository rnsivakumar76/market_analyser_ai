"""
Comprehensive unit tests for domain/signals/.

Tests cover: scoring engine, hard filters, and conflict detector.
All tests use primitive types only — no Pydantic models, no pandas.
"""

import pytest

from domain.signals.scoring_engine import (
    compute_trend_score,
    compute_pullback_score,
    compute_strength_score,
    compute_composite_score,
    classify_recommendation,
    ScoreComponents,
)
from domain.signals.filter_engine import (
    apply_adx_filter,
    apply_benchmark_filter,
    apply_candle_filter,
    apply_macro_shield,
    apply_relative_strength_filter,
    apply_all_hard_filters,
)
from domain.signals.conflict_detector import (
    detect_adx_direction_mismatch,
    detect_mtf_disagreement,
    detect_signal_conflict,
)
from domain.constants import (
    SIGNAL_WEIGHT_TREND,
    SIGNAL_WEIGHT_PULLBACK,
    SIGNAL_PULLBACK_FULL_SCORE,
    SIGNAL_PULLBACK_HALF_SCORE,
    SIGNAL_PULLBACK_NO_PULLBACK,
    SIGNAL_STRENGTH_ALIGNED,
    SIGNAL_STRENGTH_COUNTER,
    FILTER_ADX_THRESHOLD,
    SIGNAL_CONVICTION_THRESHOLD,
    CONFLICT_STRONG_ADX,
)


# ═══════════════════════════════════════════════════════════════════════════
# Scoring Engine — compute_trend_score
# ═══════════════════════════════════════════════════════════════════════════

class TestTrendScore:

    def test_bullish_trend_gives_positive_score(self):
        score, reason = compute_trend_score("bullish")
        assert score == SIGNAL_WEIGHT_TREND
        assert "uptrend" in reason.lower()

    def test_bearish_trend_gives_negative_score(self):
        score, reason = compute_trend_score("bearish")
        assert score == -SIGNAL_WEIGHT_TREND
        assert "downtrend" in reason.lower()

    def test_neutral_trend_gives_zero_score(self):
        score, reason = compute_trend_score("neutral")
        assert score == 0
        assert "unclear" in reason.lower()

    def test_trend_score_symmetric(self):
        bull_score, _ = compute_trend_score("bullish")
        bear_score, _ = compute_trend_score("bearish")
        assert bull_score == -bear_score


# ═══════════════════════════════════════════════════════════════════════════
# Scoring Engine — compute_pullback_score
# ═══════════════════════════════════════════════════════════════════════════

class TestPullbackScore:

    def test_bullish_pullback_at_support_full_score(self):
        score, reason = compute_pullback_score("bullish", pullback_detected=True, near_support=True)
        assert score == SIGNAL_PULLBACK_FULL_SCORE
        assert "ideal entry" in reason.lower()

    def test_bullish_pullback_not_at_support_half_score(self):
        score, reason = compute_pullback_score("bullish", pullback_detected=True, near_support=False)
        assert score == SIGNAL_PULLBACK_HALF_SCORE
        assert "waiting" in reason.lower()

    def test_bullish_no_pullback_small_score(self):
        score, reason = compute_pullback_score("bullish", pullback_detected=False, near_support=False)
        assert score == SIGNAL_PULLBACK_NO_PULLBACK
        assert "extended" in reason.lower()

    def test_bearish_bounce_at_support_negative(self):
        score, reason = compute_pullback_score("bearish", pullback_detected=True, near_support=True)
        assert score < 0
        assert "short entry" in reason.lower()

    def test_bearish_no_pullback_more_negative(self):
        score_bounce, _ = compute_pullback_score("bearish", pullback_detected=True, near_support=True)
        score_cont, _ = compute_pullback_score("bearish", pullback_detected=False, near_support=False)
        assert score_cont < score_bounce

    def test_neutral_trend_zero_pullback_score(self):
        score, _ = compute_pullback_score("neutral", pullback_detected=True, near_support=True)
        assert score == 0


# ═══════════════════════════════════════════════════════════════════════════
# Scoring Engine — compute_strength_score
# ═══════════════════════════════════════════════════════════════════════════

class TestStrengthScore:

    def test_bullish_strength_aligned_with_bullish_trend(self):
        score, reason = compute_strength_score("bullish", "bullish")
        assert score == SIGNAL_STRENGTH_ALIGNED
        assert "confirms" in reason.lower()

    def test_bullish_strength_against_bearish_trend(self):
        score, reason = compute_strength_score("bullish", "bearish")
        assert score == SIGNAL_STRENGTH_COUNTER
        assert "against trend" in reason.lower()

    def test_bearish_strength_aligned_with_bearish_trend(self):
        score, reason = compute_strength_score("bearish", "bearish")
        assert score == -SIGNAL_STRENGTH_ALIGNED

    def test_bearish_strength_against_bullish_trend(self):
        score, reason = compute_strength_score("bearish", "bullish")
        assert score == -SIGNAL_STRENGTH_COUNTER

    def test_neutral_strength_returns_zero(self):
        score, _ = compute_strength_score("neutral", "bullish")
        assert score == 0


# ═══════════════════════════════════════════════════════════════════════════
# Scoring Engine — compute_composite_score
# ═══════════════════════════════════════════════════════════════════════════

class TestCompositeScore:

    def test_all_bullish_gives_max_positive(self):
        result = compute_composite_score("bullish", True, True, "bullish")
        assert result.composite > 0
        assert result.composite == (
            SIGNAL_WEIGHT_TREND + SIGNAL_PULLBACK_FULL_SCORE + SIGNAL_STRENGTH_ALIGNED
        )

    def test_all_bearish_gives_max_negative(self):
        result = compute_composite_score("bearish", False, False, "bearish")
        assert result.composite < 0

    def test_composite_returns_score_components(self):
        result = compute_composite_score("bullish", True, True, "bullish")
        assert isinstance(result, ScoreComponents)
        assert isinstance(result.composite, int)
        assert isinstance(result.reasons, list)

    def test_composite_has_three_reasons(self):
        result = compute_composite_score("neutral", False, False, "neutral")
        assert len(result.reasons) == 3

    def test_composite_decomposition_adds_up(self):
        result = compute_composite_score("bullish", True, False, "neutral")
        assert result.composite == (
            result.trend_score + result.pullback_score + result.strength_score
        )

    def test_composite_ideal_bullish_value(self):
        """Full ideal bullish setup: trend=40 + pullback_at_support=30 + aligned=30 = 100"""
        result = compute_composite_score("bullish", True, True, "bullish")
        assert result.composite == 100

    def test_composite_ideal_bearish_value(self):
        """Full ideal bearish setup: -40 + bearish_cont=-20 + aligned=-30 = -90"""
        result = compute_composite_score("bearish", False, False, "bearish")
        expected = -SIGNAL_WEIGHT_TREND - 20 - SIGNAL_STRENGTH_ALIGNED
        assert result.composite == expected


# ═══════════════════════════════════════════════════════════════════════════
# Scoring Engine — classify_recommendation
# ═══════════════════════════════════════════════════════════════════════════

class TestClassifyRecommendation:

    def test_above_threshold_bullish_trade_worthy(self):
        rec, tw = classify_recommendation(75, SIGNAL_CONVICTION_THRESHOLD)
        assert rec == "bullish"
        assert tw is True

    def test_below_negative_threshold_bearish_trade_worthy(self):
        rec, tw = classify_recommendation(-75, SIGNAL_CONVICTION_THRESHOLD)
        assert rec == "bearish"
        assert tw is True

    def test_moderate_positive_bullish_not_trade_worthy(self):
        rec, tw = classify_recommendation(30, SIGNAL_CONVICTION_THRESHOLD)
        assert rec == "bullish"
        assert tw is False

    def test_moderate_negative_bearish_not_trade_worthy(self):
        rec, tw = classify_recommendation(-30, SIGNAL_CONVICTION_THRESHOLD)
        assert rec == "bearish"
        assert tw is False

    def test_near_zero_neutral(self):
        rec, tw = classify_recommendation(5, SIGNAL_CONVICTION_THRESHOLD)
        assert rec == "neutral"
        assert tw is False

    def test_exactly_at_threshold(self):
        rec, tw = classify_recommendation(SIGNAL_CONVICTION_THRESHOLD, SIGNAL_CONVICTION_THRESHOLD)
        assert rec == "bullish"
        assert tw is True


# ═══════════════════════════════════════════════════════════════════════════
# Filter Engine — Individual Filters
# ═══════════════════════════════════════════════════════════════════════════

class TestADXFilter:

    def test_adx_below_threshold_blocks_trade(self):
        result = apply_adx_filter(adx=20.0, trade_worthy=True)
        assert result.blocked is True
        assert "ADX" in result.reason

    def test_adx_above_threshold_passes(self):
        result = apply_adx_filter(adx=30.0, trade_worthy=True)
        assert result.blocked is False

    def test_adx_filter_skipped_when_not_trade_worthy(self):
        result = apply_adx_filter(adx=10.0, trade_worthy=False)
        assert result.blocked is False

    def test_adx_exactly_at_threshold_blocks(self):
        result = apply_adx_filter(adx=FILTER_ADX_THRESHOLD, trade_worthy=True)
        assert result.blocked is True

    def test_adx_custom_threshold(self):
        result = apply_adx_filter(adx=30.0, trade_worthy=True, adx_threshold=35.0)
        assert result.blocked is True


class TestBenchmarkFilter:

    def test_bullish_signal_bearish_benchmark_blocked(self):
        result = apply_benchmark_filter("bullish", "bearish", trade_worthy=True)
        assert result.blocked is True
        assert "Beta Filter" in result.reason

    def test_bearish_signal_bullish_benchmark_blocked(self):
        result = apply_benchmark_filter("bearish", "bullish", trade_worthy=True)
        assert result.blocked is True

    def test_bullish_signal_bullish_benchmark_passes(self):
        result = apply_benchmark_filter("bullish", "bullish", trade_worthy=True)
        assert result.blocked is False

    def test_neutral_signal_passes_regardless_of_benchmark(self):
        result = apply_benchmark_filter("neutral", "bearish", trade_worthy=True)
        assert result.blocked is False

    def test_filter_skipped_when_not_trade_worthy(self):
        result = apply_benchmark_filter("bullish", "bearish", trade_worthy=False)
        assert result.blocked is False


class TestCandleFilter:

    def test_bullish_recommendation_no_bullish_candle_blocked(self):
        result = apply_candle_filter("bullish", True, candle_is_bullish=None, candle_pattern="Doji")
        assert result.blocked is True
        assert "Trigger Filter" in result.reason

    def test_bullish_recommendation_bearish_candle_blocked(self):
        result = apply_candle_filter("bullish", True, candle_is_bullish=False, candle_pattern="Shooting Star")
        assert result.blocked is True

    def test_bullish_recommendation_bullish_candle_passes(self):
        result = apply_candle_filter("bullish", True, candle_is_bullish=True, candle_pattern="Hammer")
        assert result.blocked is False

    def test_bearish_recommendation_bullish_candle_blocked(self):
        result = apply_candle_filter("bearish", True, candle_is_bullish=True, candle_pattern="Engulfing")
        assert result.blocked is True

    def test_bearish_recommendation_bearish_candle_passes(self):
        result = apply_candle_filter("bearish", True, candle_is_bullish=False, candle_pattern="Shooting Star")
        assert result.blocked is False

    def test_filter_skipped_when_not_trade_worthy(self):
        result = apply_candle_filter("bullish", False, candle_is_bullish=None)
        assert result.blocked is False


class TestMacroShield:

    def test_high_impact_events_blocks_trade(self):
        result, score = apply_macro_shield(has_high_impact_events=True, trade_worthy=True, current_score=80)
        assert result.blocked is True
        assert "Macro Shield" in result.reason
        assert score < 80

    def test_no_events_passes(self):
        result, score = apply_macro_shield(has_high_impact_events=False, trade_worthy=True, current_score=80)
        assert result.blocked is False
        assert score == 80

    def test_macro_shield_skipped_when_not_trade_worthy(self):
        result, score = apply_macro_shield(has_high_impact_events=True, trade_worthy=False, current_score=80)
        assert result.blocked is False

    def test_score_reduction_capped_at_minus_100(self):
        result, score = apply_macro_shield(has_high_impact_events=True, trade_worthy=True, current_score=-95)
        assert score >= -100

    def test_score_reduction_capped_at_plus_100(self):
        result, score = apply_macro_shield(has_high_impact_events=True, trade_worthy=True, current_score=5)
        assert score >= -100


class TestRelativeStrengthFilter:

    def test_bullish_laggard_blocked(self):
        result = apply_relative_strength_filter("bullish", True, is_outperforming=False)
        assert result.blocked is True
        assert "laggard" in result.reason.lower()

    def test_bearish_outperformer_blocked(self):
        result = apply_relative_strength_filter("bearish", True, is_outperforming=True)
        assert result.blocked is True
        assert "leaders" in result.reason.lower()

    def test_bullish_outperformer_passes(self):
        result = apply_relative_strength_filter("bullish", True, is_outperforming=True)
        assert result.blocked is False

    def test_bearish_laggard_passes(self):
        result = apply_relative_strength_filter("bearish", True, is_outperforming=False)
        assert result.blocked is False

    def test_filter_skipped_when_not_trade_worthy(self):
        result = apply_relative_strength_filter("bullish", False, is_outperforming=False)
        assert result.blocked is False


# ═══════════════════════════════════════════════════════════════════════════
# Filter Engine — apply_all_hard_filters
# ═══════════════════════════════════════════════════════════════════════════

class TestAllHardFilters:

    def _base_kwargs(self, **overrides):
        defaults = dict(
            recommendation="bullish",
            trade_worthy=True,
            composite_score=80,
            adx=30.0,
            benchmark_direction="bullish",
            candle_is_bullish=True,
            candle_pattern="Hammer",
            has_high_impact_events=False,
            is_outperforming=True,
        )
        defaults.update(overrides)
        return defaults

    def test_all_pass_gives_trade_worthy(self):
        tw, score, reasons = apply_all_hard_filters(**self._base_kwargs())
        assert tw is True
        assert reasons == []

    def test_adx_failure_blocks(self):
        tw, score, reasons = apply_all_hard_filters(**self._base_kwargs(adx=15.0))
        assert tw is False
        assert len(reasons) >= 1
        assert any("ADX" in r for r in reasons)

    def test_macro_shield_blocks_and_adjusts_score(self):
        tw, score, reasons = apply_all_hard_filters(
            **self._base_kwargs(has_high_impact_events=True)
        )
        assert tw is False
        assert score < 80

    def test_multiple_filters_all_reasons_collected(self):
        tw, score, reasons = apply_all_hard_filters(
            **self._base_kwargs(adx=10.0, benchmark_direction="bearish")
        )
        assert tw is False
        assert len(reasons) >= 2

    def test_no_outperformance_data_skips_rs_filter(self):
        kwargs = self._base_kwargs()
        kwargs["is_outperforming"] = None
        tw, score, reasons = apply_all_hard_filters(**kwargs)
        assert tw is True


# ═══════════════════════════════════════════════════════════════════════════
# Conflict Detector Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestConflictDetector:

    def test_strong_adx_neutral_gives_high_severity(self):
        result = detect_adx_direction_mismatch(adx=40.0, recommendation="neutral")
        assert result.conflict_type == "adx_direction_mismatch"
        assert result.severity == "high"

    def test_strong_adx_bullish_no_conflict(self):
        result = detect_adx_direction_mismatch(adx=40.0, recommendation="bullish")
        assert result.conflict_type == "none"

    def test_weak_adx_neutral_no_conflict(self):
        result = detect_adx_direction_mismatch(adx=20.0, recommendation="neutral")
        assert result.conflict_type == "none"

    def test_adx_mismatch_includes_trigger_prices(self):
        result = detect_adx_direction_mismatch(
            adx=40.0, recommendation="neutral",
            trigger_up=105.0, trigger_down=95.0
        )
        assert result.trigger_price_up == 105.0
        assert result.trigger_price_down == 95.0

    def test_adx_mismatch_guidance_contains_price(self):
        result = detect_adx_direction_mismatch(
            adx=40.0, recommendation="neutral",
            trigger_up=105.0, trigger_down=95.0
        )
        assert "105.00" in result.guidance
        assert "95.00" in result.guidance

    def test_mtf_disagreement_bullish_trend_bearish_strength(self):
        result = detect_mtf_disagreement("bullish", "bearish")
        assert result.conflict_type == "mtf_disagreement"
        assert result.severity == "medium"
        assert "dip-buy" in result.guidance.lower()

    def test_mtf_disagreement_bearish_trend_bullish_strength(self):
        result = detect_mtf_disagreement("bearish", "bullish")
        assert result.conflict_type == "mtf_disagreement"
        assert result.severity == "medium"
        assert "dead cat" in result.guidance.lower()

    def test_mtf_no_conflict_aligned(self):
        result = detect_mtf_disagreement("bullish", "bullish")
        assert result.conflict_type == "none"

    def test_mtf_no_conflict_neutral(self):
        result = detect_mtf_disagreement("neutral", "neutral")
        assert result.conflict_type == "none"

    def test_detect_signal_conflict_adx_takes_priority(self):
        """ADX mismatch (high) should be returned before MTF disagreement (medium)."""
        result = detect_signal_conflict(
            adx=40.0,
            recommendation="neutral",
            trend_direction="bullish",
            strength_direction="bearish",
        )
        assert result.conflict_type == "adx_direction_mismatch"
        assert result.severity == "high"

    def test_detect_signal_conflict_falls_through_to_mtf(self):
        result = detect_signal_conflict(
            adx=20.0,  # weak ADX — no mismatch
            recommendation="bullish",
            trend_direction="bullish",
            strength_direction="bearish",
        )
        assert result.conflict_type == "mtf_disagreement"

    def test_detect_signal_conflict_no_conflict(self):
        result = detect_signal_conflict(
            adx=20.0,
            recommendation="bullish",
            trend_direction="bullish",
            strength_direction="bullish",
        )
        assert result.conflict_type == "none"
        assert result.severity == "none"

    def test_adx_mismatch_custom_threshold(self):
        result = detect_adx_direction_mismatch(
            adx=32.0, recommendation="neutral",
            strong_adx_threshold=35.0
        )
        assert result.conflict_type == "none"
        result2 = detect_adx_direction_mismatch(
            adx=36.0, recommendation="neutral",
            strong_adx_threshold=35.0
        )
        assert result2.conflict_type == "adx_direction_mismatch"
