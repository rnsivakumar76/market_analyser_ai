"""
Tests for signal_generator.generate_trade_signal — every code branch.
Covers: scoring logic, all 5 hard filters, executive summary text,
        score clamping, conflict detection.
Run:  pytest tests/test_signal_generator.py -v
"""
import pytest

from app.models import (
    Signal, TrendAnalysis, PullbackAnalysis, StrengthAnalysis,
    CandleAnalysis, StrategySettings, FundamentalsAnalysis,
    RelativeStrengthAnalysis, TechnicalAnalysis, PivotPoints,
    FibonacciLevels, VolatilityAnalysis
)
from app.signal_generator import generate_trade_signal


# ---------------------------------------------------------------------------
# Fixtures — minimal valid model instances
# ---------------------------------------------------------------------------

def _trend(direction=Signal.BULLISH) -> TrendAnalysis:
    return TrendAnalysis(
        direction=direction, fast_ma=100.0, slow_ma=90.0,
        price_above_fast_ma=True, price_above_slow_ma=True,
        description="test"
    )


def _pullback(detected=True, near_support=True) -> PullbackAnalysis:
    return PullbackAnalysis(
        detected=detected, pullback_percent=5.0,
        near_support=near_support, support_level=95.0,
        description="test"
    )


def _strength(signal=Signal.BULLISH, adx=30.0) -> StrengthAnalysis:
    return StrengthAnalysis(
        signal=signal, rsi=55.0, volume_ratio=1.2,
        adx=adx, price_change_percent=1.5, description="test"
    )


def _candle(is_bullish=True) -> CandleAnalysis:
    return CandleAnalysis(
        pattern="Hammer",
        description="Bullish hammer at support",
        is_bullish=is_bullish
    )


def _settings(conviction=70, adx_threshold=25, mode="balanced") -> StrategySettings:
    return StrategySettings(
        conviction_threshold=conviction,
        adx_threshold=adx_threshold,
        atr_multiplier_tp=3.0,
        atr_multiplier_sl=1.5,
        portfolio_value=10000.0,
        risk_per_trade_percent=1.0,
        aggressiveness_mode=mode,
    )


def _fundamentals(has_events=False) -> FundamentalsAnalysis:
    return FundamentalsAnalysis(
        has_high_impact_events=has_events,
        events=["NFP +48h"] if has_events else [],
        description="test"
    )


def _rs(is_outperforming=True, label="Leader") -> RelativeStrengthAnalysis:
    return RelativeStrengthAnalysis(
        is_outperforming=is_outperforming,
        symbol_return=5.0, benchmark_return=2.0,
        alpha=3.0, label=label, description="test"
    )


def _tech() -> TechnicalAnalysis:
    return TechnicalAnalysis(
        pivot_points=PivotPoints(
            pivot=100.0, r1=105.0, r2=110.0, r3=115.0,
            s1=95.0, s2=90.0, s3=85.0
        ),
        fibonacci=FibonacciLevels(
            trend="bullish", swing_high=110.0, swing_low=85.0,
            ret_382=95.4, ret_500=97.5, ret_618=99.6,
            ext_1272=118.0, ext_1618=125.5
        ),
        least_resistance_line="up",
        trend_breakout="none",
        breakout_confidence=0.0,
        description="test"
    )


def _volatility(current_price=100.0) -> VolatilityAnalysis:
    return VolatilityAnalysis(
        atr=2.0, stop_loss=96.0, take_profit=112.0,
        take_profit_level1=104.0, take_profit_level2=108.0,
        risk_reward_ratio=3.0, description="test"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def full_bullish_signal(**overrides):
    """All conditions for a high-conviction bullish trade-worthy signal."""
    kwargs = dict(
        trend=_trend(Signal.BULLISH),
        pullback=_pullback(detected=True, near_support=True),
        strength=_strength(Signal.BULLISH, adx=35.0),
        candle=_candle(is_bullish=True),
        benchmark_direction=Signal.BULLISH,
        settings=_settings(conviction=70, adx_threshold=25),
        current_price=100.0,
        tech_indicators=_tech(),
        volatility=_volatility(),
        fundamentals=_fundamentals(has_events=False),
        relative_strength=_rs(is_outperforming=True, label="Leader"),
    )
    kwargs.update(overrides)
    return generate_trade_signal(**kwargs)


def full_bearish_signal(**overrides):
    """All conditions for a high-conviction bearish trade-worthy signal."""
    kwargs = dict(
        trend=_trend(Signal.BEARISH),
        pullback=_pullback(detected=False, near_support=False),
        strength=_strength(Signal.BEARISH, adx=35.0),
        candle=_candle(is_bullish=False),
        benchmark_direction=Signal.BEARISH,
        settings=_settings(conviction=70, adx_threshold=25),
        current_price=100.0,
        tech_indicators=_tech(),
        volatility=_volatility(),
        fundamentals=_fundamentals(has_events=False),
        relative_strength=_rs(is_outperforming=False, label="Laggard"),
    )
    kwargs.update(overrides)
    return generate_trade_signal(**kwargs)


# ---------------------------------------------------------------------------
# 1. Score calculation
# ---------------------------------------------------------------------------

class TestScoreCalculation:

    def test_full_bullish_score_above_threshold(self):
        sig = full_bullish_signal()
        # Monthly(40) + Pullback-at-support(30) + Daily-confirms(30) = 100
        assert sig.score >= 70, f"Expected score ≥ 70, got {sig.score}"
        assert sig.trade_worthy is True

    def test_full_bearish_score_below_threshold(self):
        sig = full_bearish_signal()
        # Monthly(-40) + Downtrend-continuation(-20) + Daily-confirms(-30) = -90
        assert sig.score <= -70, f"Expected score ≤ -70, got {sig.score}"
        assert sig.trade_worthy is True

    def test_neutral_score_near_zero(self):
        sig = generate_trade_signal(
            trend=_trend(Signal.NEUTRAL),
            pullback=_pullback(detected=False, near_support=False),
            strength=_strength(Signal.NEUTRAL, adx=10.0),
            candle=_candle(is_bullish=None),
            settings=_settings(),
        )
        assert -20 <= sig.score <= 20
        assert sig.recommendation == Signal.NEUTRAL

    def test_score_clamped_to_100(self):
        """Score must never exceed ±100 regardless of boosts applied downstream."""
        sig = full_bullish_signal()
        assert -100 <= sig.score <= 100

    def test_pullback_without_support_partial_score(self):
        """Pullback detected but not at support → +15 (not +30)."""
        sig = generate_trade_signal(
            trend=_trend(Signal.BULLISH),
            pullback=_pullback(detected=True, near_support=False),
            strength=_strength(Signal.BULLISH, adx=35.0),
            candle=_candle(is_bullish=True),
            benchmark_direction=Signal.BULLISH,
            settings=_settings(),
        )
        # TRENDING regime (ADX=35): trend=50 + pullback_half=10 + strength=30 = 90
        assert sig.score == 90

    def test_no_pullback_small_bonus(self):
        """No pullback in uptrend → +5."""
        sig = generate_trade_signal(
            trend=_trend(Signal.BULLISH),
            pullback=_pullback(detected=False, near_support=False),
            strength=_strength(Signal.BULLISH, adx=35.0),
            candle=_candle(is_bullish=True),
            benchmark_direction=Signal.BULLISH,
            settings=_settings(),
        )
        # TRENDING regime (ADX=35): trend=50 + no_pb=round(20*5/30)=3 + strength=30 = 83
        assert sig.score == 83

    def test_contextual_boosts_applied_before_final_classification(self):
        sig = generate_trade_signal(
            trend=_trend(Signal.BULLISH),
            pullback=_pullback(detected=False, near_support=False),
            strength=_strength(Signal.BULLISH, adx=35.0),
            candle=_candle(is_bullish=True),
            benchmark_direction=Signal.BULLISH,
            settings=_settings(conviction=70, adx_threshold=25),
            current_price=100.0,
            tech_indicators=TechnicalAnalysis(
                pivot_points=PivotPoints(
                    pivot=100.0, r1=105.0, r2=110.0, r3=115.0,
                    s1=95.0, s2=90.0, s3=85.0
                ),
                fibonacci=FibonacciLevels(
                    trend="bullish", swing_high=110.0, swing_low=85.0,
                    ret_382=95.4, ret_500=97.5, ret_618=99.6,
                    ext_1272=118.0, ext_1618=125.5
                ),
                least_resistance_line="up",
                trend_breakout="bullish_breakout",
                breakout_confidence=0.8,
                description="test"
            ),
            fundamentals=_fundamentals(has_events=False),
            relative_strength=_rs(is_outperforming=True, label="Leader"),
            news_sentiment_label="bullish"
        )

        # Base score would be 83; contextual boosts should push to capped 100 before final classification.
        assert sig.score == 100
        assert sig.recommendation == Signal.BULLISH
        assert sig.trade_worthy is True
        assert any("Bullish Breakout" in r for r in sig.reasons)


# ---------------------------------------------------------------------------
# 2. Hard Filter 1 — ADX threshold
# ---------------------------------------------------------------------------

class TestHardFilterADX:

    def test_low_adx_blocks_trade_worthy(self):
        sig = full_bullish_signal(
            strength=_strength(Signal.BULLISH, adx=15.0),
            settings=_settings(adx_threshold=25)
        )
        assert sig.trade_worthy is False
        assert any("ADX" in r for r in sig.reasons)

    def test_adx_exactly_at_threshold_blocks(self):
        """ADX must be ABOVE threshold, not equal."""
        sig = full_bullish_signal(
            strength=_strength(Signal.BULLISH, adx=25.0),
            settings=_settings(adx_threshold=25)
        )
        assert sig.trade_worthy is False

    def test_adx_above_threshold_passes(self):
        sig = full_bullish_signal(
            strength=_strength(Signal.BULLISH, adx=26.0),
            settings=_settings(adx_threshold=25)
        )
        assert sig.trade_worthy is True

    def test_adx_zero_blocks_trade(self):
        """ADX=0 (no trend) must block trade."""
        sig = full_bullish_signal(
            strength=_strength(Signal.BULLISH, adx=0.0),
            settings=_settings(adx_threshold=25)
        )
        assert sig.trade_worthy is False
        assert any("ADX" in r for r in sig.reasons)


# ---------------------------------------------------------------------------
# 3. Hard Filter 2 — Benchmark direction
# ---------------------------------------------------------------------------

class TestHardFilterBenchmark:

    def test_buying_in_bearish_market_blocked(self):
        sig = full_bullish_signal(benchmark_direction=Signal.BEARISH)
        assert sig.trade_worthy is False
        assert any("Beta Filter" in r for r in sig.reasons)

    def test_shorting_in_bullish_market_blocked(self):
        sig = full_bearish_signal(benchmark_direction=Signal.BULLISH)
        assert sig.trade_worthy is False
        assert any("Beta Filter" in r for r in sig.reasons)

    def test_neutral_benchmark_does_not_block(self):
        sig = full_bullish_signal(benchmark_direction=Signal.NEUTRAL)
        assert sig.trade_worthy is True


# ---------------------------------------------------------------------------
# 4. Hard Filter 3 — Candle trigger
# ---------------------------------------------------------------------------

class TestHardFilterCandle:

    def test_no_bullish_candle_blocks_buy(self):
        sig = full_bullish_signal(candle=_candle(is_bullish=False))
        assert sig.trade_worthy is False
        assert any("Trigger Filter" in r for r in sig.reasons)

    def test_no_bearish_candle_blocks_short(self):
        sig = full_bearish_signal(candle=_candle(is_bullish=True))
        assert sig.trade_worthy is False
        assert any("Trigger Filter" in r for r in sig.reasons)

    def test_none_candle_blocks_both(self):
        sig_bull = full_bullish_signal(candle=_candle(is_bullish=None))
        assert sig_bull.trade_worthy is False

    def test_correct_candle_passes(self):
        sig = full_bullish_signal(candle=_candle(is_bullish=True))
        assert sig.trade_worthy is True
        assert any("Price Action Trigger confirmed" in r for r in sig.reasons)


# ---------------------------------------------------------------------------
# 5. Hard Filter 4 — Fundamental event guard
# ---------------------------------------------------------------------------

class TestHardFilterFundamentals:

    def test_high_impact_event_penalizes_score_and_warns(self):
        sig = full_bullish_signal(fundamentals=_fundamentals(has_events=True))
        assert sig.score == 80  # 100 base (capped) then -20 macro penalty
        assert any("Macro Caution" in r for r in sig.reasons)

    def test_no_event_does_not_block(self):
        sig = full_bullish_signal(fundamentals=_fundamentals(has_events=False))
        assert sig.trade_worthy is True

    def test_none_fundamentals_does_not_block(self):
        sig = full_bullish_signal(fundamentals=None)
        assert sig.trade_worthy is True


# ---------------------------------------------------------------------------
# 6. Hard Filter 5 — Relative Strength (alpha shield)
# ---------------------------------------------------------------------------

class TestHardFilterRelativeStrength:

    def test_laggard_blocks_buy(self):
        sig = full_bullish_signal(
            relative_strength=_rs(is_outperforming=False, label="Laggard")
        )
        assert sig.trade_worthy is False
        assert any("Alpha Filter" in r for r in sig.reasons)

    def test_leader_allows_buy(self):
        sig = full_bullish_signal(
            relative_strength=_rs(is_outperforming=True, label="Leader")
        )
        assert sig.trade_worthy is True

    def test_outperformer_blocks_short(self):
        sig = full_bearish_signal(
            relative_strength=_rs(is_outperforming=True, label="Leader")
        )
        assert sig.trade_worthy is False
        assert any("Alpha Filter" in r for r in sig.reasons)

    def test_none_rs_does_not_block(self):
        sig = full_bullish_signal(relative_strength=None)
        assert sig.trade_worthy is True


# ---------------------------------------------------------------------------
# 7. Executive summary text correctness
# ---------------------------------------------------------------------------

class TestExecutiveSummary:

    def test_bullish_trade_worthy_summary(self):
        sig = full_bullish_signal()
        assert "BUY setup is active" in sig.executive_summary
        assert "uptrend" in sig.executive_summary

    def test_bullish_not_trade_worthy_summary(self):
        sig = full_bullish_signal(
            strength=_strength(Signal.BULLISH, adx=15.0)
        )
        assert "execution is conditional" in sig.executive_summary
        assert "trigger" in sig.executive_summary

    def test_bearish_trade_worthy_summary(self):
        sig = full_bearish_signal()
        assert "SELL setup is active" in sig.executive_summary
        assert "downtrend" in sig.executive_summary

    def test_neutral_summary(self):
        sig = generate_trade_signal(
            trend=_trend(Signal.NEUTRAL),
            pullback=_pullback(False, False),
            strength=_strength(Signal.NEUTRAL, adx=10.0),
            candle=_candle(None),
            settings=_settings(),
        )
        assert "neutral" in sig.executive_summary.lower()

    def test_fundamental_event_warning_in_summary(self):
        sig = full_bullish_signal(fundamentals=_fundamentals(has_events=True))
        assert "violent swings" in sig.executive_summary

    def test_summary_is_nonempty_string(self):
        for direction in [Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL]:
            sig = generate_trade_signal(
                trend=_trend(direction),
                pullback=_pullback(),
                strength=_strength(Signal.NEUTRAL, adx=10.0),
                candle=_candle(None),
                settings=_settings(),
            )
            assert isinstance(sig.executive_summary, str)
            assert len(sig.executive_summary) > 20


# ---------------------------------------------------------------------------
# 8. Action plan and scaling plan correctness
# ---------------------------------------------------------------------------

class TestActionPlan:

    def test_trade_worthy_bullish_has_enter_long(self):
        sig = full_bullish_signal()
        assert sig.action_plan == "Enter Long (Market)"
        assert sig.scaling_plan.startswith("Stage 1")

    def test_trade_worthy_bearish_has_enter_short(self):
        sig = full_bearish_signal()
        assert sig.action_plan == "Enter Short (Market)"

    def test_not_trade_worthy_bullish_has_wait(self):
        sig = full_bullish_signal(strength=_strength(Signal.BULLISH, adx=10.0))
        assert "Conditional" in sig.action_plan

    def test_neutral_has_observe(self):
        sig = generate_trade_signal(
            trend=_trend(Signal.NEUTRAL),
            pullback=_pullback(False, False),
            strength=_strength(Signal.NEUTRAL, adx=10.0),
            candle=_candle(None),
            settings=_settings(),
        )
        assert "Observe" in sig.action_plan or "Aside" in sig.action_plan


# ---------------------------------------------------------------------------
# 9. Signal conflict detection
# ---------------------------------------------------------------------------

class TestSignalConflict:

    def test_mtf_bullish_trend_bearish_daily_detected(self):
        sig = generate_trade_signal(
            trend=_trend(Signal.BULLISH),
            pullback=_pullback(),
            strength=_strength(Signal.BEARISH, adx=30.0),
            candle=_candle(None),
            settings=_settings(),
        )
        assert sig.signal_conflict is not None
        assert sig.signal_conflict.conflict_type == "mtf_disagreement"
        assert sig.signal_conflict.severity == "medium"

    def test_no_conflict_in_aligned_signal(self):
        sig = full_bullish_signal()
        assert sig.signal_conflict is not None
        assert sig.signal_conflict.conflict_type == "none"

    def test_adx_direction_mismatch_detected(self):
        """Strong ADX but recommendation ends up NEUTRAL."""
        sig = generate_trade_signal(
            trend=_trend(Signal.NEUTRAL),
            pullback=_pullback(False, False),
            strength=_strength(Signal.NEUTRAL, adx=40.0),
            candle=_candle(None),
            settings=_settings(),
        )
        if sig.recommendation == Signal.NEUTRAL:
            assert sig.signal_conflict.conflict_type == "adx_direction_mismatch"


# ---------------------------------------------------------------------------
# 11. Execution profile fields
# ---------------------------------------------------------------------------

class TestExecutionProfile:

    def test_ready_state_and_grade_for_trade_worthy_signal(self):
        sig = full_bullish_signal()
        assert sig.execution_state == "ready"
        assert sig.opportunity_grade in {"A", "B"}
        assert "x (" in sig.suggested_size_text

    def test_conditional_state_for_non_trade_worthy_directional_bias(self):
        sig = full_bullish_signal(strength=_strength(Signal.BULLISH, adx=10.0))
        assert sig.recommendation == Signal.BULLISH
        assert sig.trade_worthy is False
        assert sig.execution_state == "conditional"
        assert sig.opportunity_grade in {"B", "C"}

    def test_stand_aside_for_neutral_signal(self):
        sig = generate_trade_signal(
            trend=_trend(Signal.NEUTRAL),
            pullback=_pullback(False, False),
            strength=_strength(Signal.NEUTRAL, adx=10.0),
            candle=_candle(None),
            settings=_settings(),
        )
        assert sig.recommendation == Signal.NEUTRAL
        assert sig.execution_state == "stand_aside"
        assert sig.opportunity_grade == "D"


# ---------------------------------------------------------------------------
# 12. Aggressiveness mode behavior
# ---------------------------------------------------------------------------

class TestAggressivenessMode:

    def test_aggressive_mode_can_activate_trade_that_balanced_keeps_conditional(self):
        common_kwargs = dict(
            trend=_trend(Signal.BULLISH),
            pullback=_pullback(detected=False, near_support=False),
            strength=_strength(Signal.NEUTRAL, adx=30.0),
            candle=_candle(is_bullish=True),
            benchmark_direction=Signal.BULLISH,
            tech_indicators=_tech(),
            fundamentals=_fundamentals(False),
            relative_strength=None,
            news_sentiment_label="bullish",
        )

        sig_balanced = generate_trade_signal(
            settings=_settings(conviction=70, adx_threshold=25, mode="balanced"),
            **common_kwargs,
        )
        sig_aggressive = generate_trade_signal(
            settings=_settings(conviction=70, adx_threshold=25, mode="aggressive"),
            **common_kwargs,
        )

        assert sig_balanced.score == sig_aggressive.score == 63
        assert sig_balanced.trade_worthy is False
        assert sig_balanced.execution_state == "conditional"
        assert sig_aggressive.trade_worthy is True
        assert sig_aggressive.execution_state == "ready"

    def test_conservative_mode_uses_smaller_sizing_than_aggressive_for_conditional(self):
        common_kwargs = dict(
            trend=_trend(Signal.BULLISH),
            pullback=_pullback(detected=False, near_support=False),
            strength=_strength(Signal.BULLISH, adx=15.0),
            candle=_candle(is_bullish=True),
            benchmark_direction=Signal.BULLISH,
            tech_indicators=_tech(),
            fundamentals=_fundamentals(False),
            relative_strength=None,
            news_sentiment_label=None,
        )

        sig_conservative = generate_trade_signal(
            settings=_settings(conviction=70, adx_threshold=25, mode="conservative"),
            **common_kwargs,
        )
        sig_aggressive = generate_trade_signal(
            settings=_settings(conviction=70, adx_threshold=25, mode="aggressive"),
            **common_kwargs,
        )

        assert sig_conservative.execution_state == "conditional"
        assert sig_aggressive.execution_state == "conditional"
        assert "0.35x" in sig_conservative.suggested_size_text
        assert "0.65x" in sig_aggressive.suggested_size_text


# ---------------------------------------------------------------------------
# 10. Robustness — missing / None optional inputs
# ---------------------------------------------------------------------------

class TestRobustnessMissingInputs:

    def test_no_tech_indicators_does_not_crash(self):
        sig = generate_trade_signal(
            trend=_trend(Signal.BULLISH),
            pullback=_pullback(),
            strength=_strength(Signal.BULLISH, adx=30.0),
            candle=_candle(True),
            settings=_settings(),
            tech_indicators=None,
            volatility=None,
        )
        assert sig is not None
        assert isinstance(sig.score, int)

    def test_no_settings_uses_defaults(self):
        sig = generate_trade_signal(
            trend=_trend(Signal.BULLISH),
            pullback=_pullback(),
            strength=_strength(Signal.BULLISH, adx=30.0),
            candle=_candle(True),
            settings=None,
        )
        assert sig is not None

    def test_no_current_price_does_not_crash(self):
        sig = full_bullish_signal(current_price=None)
        assert sig is not None

    def test_zero_current_price_does_not_crash(self):
        sig = full_bullish_signal(current_price=0.0)
        assert sig is not None
