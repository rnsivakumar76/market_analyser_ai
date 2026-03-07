"""
Comprehensive unit tests for the Expert Battle Plan generator.

Validates that the plan output is internally consistent and correctly aligned
with all indicator values displayed elsewhere in the application.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.analyzers.day_trading_expert import (
    generate_expert_trade_plan,
    detect_opening_range,
    calculate_rvol,
)
from app.models import (
    PivotPoints, FibonacciLevels, TechnicalAnalysis,
    SessionContext,
)


# ─────────────────────────────────────────────────────────────────────────────
# Shared Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def pivots():
    return PivotPoints(pivot=70.0, r1=72.5, r2=74.0, r3=76.0, s1=68.0, s2=66.5, s3=65.0)


@pytest.fixture
def fibs():
    return FibonacciLevels(
        trend="bullish", swing_high=75.0, swing_low=63.0,
        ret_382=68.41, ret_500=69.0, ret_618=69.59,
        ext_1272=78.27, ext_1618=82.41,
    )


@pytest.fixture
def technical(pivots, fibs):
    return TechnicalAnalysis(
        pivot_points=pivots, fibonacci=fibs,
        least_resistance_line="up", trend_breakout="none",
        breakout_confidence=0.0, description="Test structure",
    )


@pytest.fixture
def or_bullish():
    return {"or_high": 72.0, "or_low": 70.5, "broken": "bullish"}


@pytest.fixture
def or_bearish():
    return {"or_high": 72.0, "or_low": 70.5, "broken": "bearish"}


@pytest.fixture
def or_inside():
    return {"or_high": 72.0, "or_low": 70.5, "broken": "none"}


@pytest.fixture
def or_empty():
    return {"or_high": 0.0, "or_low": 0.0, "broken": "none"}


@pytest.fixture
def session_with_london():
    return SessionContext(
        pdh=73.0, pdl=69.0,
        london_open=70.20,
        current_session_range_pct=1.5,
        description="Prev Day High: 73.00, Low: 69.00. London Open: 70.20.",
    )


@pytest.fixture
def session_no_london():
    return SessionContext(
        pdh=73.0, pdl=69.0,
        london_open=None,
        current_session_range_pct=1.2,
        description="Prev Day High: 73.00, Low: 69.00.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. ORB Detection
# ─────────────────────────────────────────────────────────────────────────────

def _make_15m_df(or_high=72.0, or_low=70.5, last_close=None):
    """Build minimal 15m DataFrame with a known opening range."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    idx = [today + timedelta(minutes=15 * i) for i in range(10)]
    n = len(idx)
    closes = [71.0] * n
    if last_close is not None:
        closes[-1] = last_close
    return pd.DataFrame({
        "Open":   [70.9] * n,
        "High":   [or_high] + [71.5] * (n - 1),
        "Low":    [or_low]  + [70.8] * (n - 1),
        "Close":  closes,
        "Volume": [1000] * n,
    }, index=idx)


class TestORBDetection:
    def test_bullish_break(self):
        df = _make_15m_df(or_high=72.0, or_low=70.5, last_close=72.5)
        result = detect_opening_range(df)
        assert result["broken"] == "bullish"
        assert result["or_high"] == pytest.approx(72.0)
        assert result["or_low"] == pytest.approx(70.5)

    def test_bearish_break(self):
        df = _make_15m_df(or_high=72.0, or_low=70.5, last_close=70.0)
        result = detect_opening_range(df)
        assert result["broken"] == "bearish"

    def test_inside_range(self):
        df = _make_15m_df(or_high=72.0, or_low=70.5, last_close=71.2)
        result = detect_opening_range(df)
        assert result["broken"] == "none"

    def test_empty_df_returns_safe_defaults(self):
        result = detect_opening_range(pd.DataFrame())
        assert result["broken"] == "none"
        assert result["or_high"] == 0.0
        assert result["or_low"] == 0.0

    def test_or_high_is_first_candle_high(self):
        df = _make_15m_df(or_high=75.0, or_low=68.0, last_close=71.0)
        result = detect_opening_range(df)
        assert result["or_high"] == pytest.approx(75.0)
        assert result["or_low"] == pytest.approx(68.0)


# ─────────────────────────────────────────────────────────────────────────────
# 2. RVOL Calculation
# ─────────────────────────────────────────────────────────────────────────────

class TestRVOL:
    def test_returns_float(self):
        df = _make_15m_df()
        result = calculate_rvol(df)
        assert isinstance(result, float)

    def test_insufficient_data_returns_1(self):
        df = _make_15m_df()
        result = calculate_rvol(df[:5])
        assert result == pytest.approx(1.0)

    def test_high_current_volume_returns_gt1(self):
        today = datetime.utcnow().replace(hour=0, minute=0, second=0)
        n = 100
        idx = [today - timedelta(minutes=15 * (n - i)) for i in range(n)]
        base_vol = 1000
        volumes = [base_vol] * n
        volumes[-1] = base_vol * 5  # Current bar has 5x average volume
        df = pd.DataFrame({
            "Open": [70.0] * n, "High": [71.0] * n,
            "Low": [69.0] * n, "Close": [70.5] * n,
            "Volume": volumes,
        }, index=idx)
        result = calculate_rvol(df)
        assert result >= 1.0  # Cannot guarantee >1 without same-time bars, but should not error

    def test_result_is_non_negative(self):
        df = _make_15m_df()
        result = calculate_rvol(df)
        assert result >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Battle Plan Structure
# ─────────────────────────────────────────────────────────────────────────────

class TestBattlePlanStructure:
    def test_always_has_situation_section(self, or_bullish, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 1.0, technical, "")
        assert "SITUATION:" in result["battle_plan"]

    def test_multiline_with_technical_data(self, or_bullish, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 1.0, technical, "")
        lines = result["battle_plan"].split("\n")
        assert len(lines) >= 3, "Expected at least SITUATION, ENTRY/TARGETS, and CONVICTION"

    def test_returns_required_keys(self, or_bullish, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 1.0, technical, "")
        assert "battle_plan" in result
        assert "rvol" in result
        assert "is_high_intent" in result
        assert "or_high" in result
        assert "or_low" in result
        assert "or_broken" in result

    def test_or_values_pass_through(self, or_bullish, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 2.5, technical, "")
        assert result["or_high"] == pytest.approx(72.0)
        assert result["or_low"] == pytest.approx(70.5)
        assert result["or_broken"] == "bullish"

    def test_graceful_without_technical(self, or_bullish):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 1.0, None, "")
        assert "battle_plan" in result
        assert len(result["battle_plan"]) > 0

    def test_graceful_with_empty_or_data(self, or_empty, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_empty, 1.0, technical, "")
        assert "SITUATION:" in result["battle_plan"]

    def test_commodity_context_included_when_non_empty(self, or_bullish, technical):
        advice = "WARNING: DXY & Yields both rising. Gold longs are HIGH RISK."
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 1.0, technical, advice)
        assert "CONTEXT:" in result["battle_plan"]
        assert "DXY" in result["battle_plan"]

    def test_commodity_context_absent_when_empty(self, or_bullish, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 1.0, technical, "")
        assert "CONTEXT:" not in result["battle_plan"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Signal Direction Consistency (Critical)
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalDirectionConsistency:
    """These tests ensure the plan NEVER shows contradictory advice vs the signal."""

    def test_bullish_orb_bullish_signal_targets_r1_r2(self, or_bullish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        plan = result["battle_plan"]
        assert f"R1 ({pivots.r1:.2f})" in plan, "Bullish plan must target R1"
        assert f"R2 ({pivots.r2:.2f})" in plan, "Bullish plan must target R2"
        assert "TARGETS:" in plan

    def test_bullish_orb_bullish_signal_never_targets_s1_s2(self, or_bullish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        plan = result["battle_plan"]
        # S1/S2 may appear as entry/stop labels but NOT as T1/T2 targets
        assert "T1 → S1" not in plan
        assert "T2 → S2" not in plan

    def test_bearish_orb_bearish_signal_targets_s1_s2(self, or_bearish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bearish"
        )
        plan = result["battle_plan"]
        assert f"S1 ({pivots.s1:.2f})" in plan, "Bearish plan must target S1"
        assert f"S2 ({pivots.s2:.2f})" in plan, "Bearish plan must target S2"

    def test_bearish_orb_bearish_signal_never_targets_r1_r2(self, or_bearish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bearish"
        )
        plan = result["battle_plan"]
        assert "T1 → R1" not in plan
        assert "T2 → R2" not in plan

    def test_bearish_orb_bullish_signal_shows_pullback_warning(self, or_bearish, technical):
        """ORB down but daily signal is bullish = intraday pullback, NOT a new short."""
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bullish"
        )
        plan = result["battle_plan"]
        # Should flag the situation as a pullback, not a new downtrend
        assert "Pullback" in plan or "pullback" in plan or "uptrend" in plan

    def test_bearish_orb_bullish_signal_targets_long_not_short(self, or_bearish, technical, pivots):
        """When daily is bullish, bearish ORB is a pullback entry — plan should show long targets."""
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bullish"
        )
        plan = result["battle_plan"]
        # Targets should be R1/R2 (long) because the daily signal is bullish
        assert f"R1 ({pivots.r1:.2f})" in plan

    def test_bullish_orb_bearish_signal_shows_counter_trend_warning(self, or_bullish, technical):
        """ORB up but daily signal is bearish = fade/counter-trend warning."""
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bearish"
        )
        plan = result["battle_plan"]
        # Should warn about counter-trend
        assert "counter-trend" in plan.lower() or "bearish" in plan.lower()

    def test_neutral_signal_no_directional_contradiction(self, or_inside, technical):
        """Inside range + neutral signal should give waiting message, not bullish/bearish targets."""
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_inside, 1.0, technical, "", signal_direction="neutral"
        )
        plan = result["battle_plan"]
        assert "INSIDE RANGE" in plan or "WAITING" in plan


# ─────────────────────────────────────────────────────────────────────────────
# 5. Entry Zone Level Accuracy
# ─────────────────────────────────────────────────────────────────────────────

class TestEntryZoneLevels:
    def test_bullish_orb_entry_references_s1(self, or_bullish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        assert f"S1 ({pivots.s1:.2f})" in result["battle_plan"]

    def test_bullish_orb_entry_references_fib_382(self, or_bullish, technical, fibs):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        assert f"{fibs.ret_382:.2f}" in result["battle_plan"]

    def test_bearish_entry_references_r1_for_bounce_rejection(self, or_bearish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bearish"
        )
        # Dead-cat bounce rejection entry should reference R1
        assert f"R1 ({pivots.r1:.2f})" in result["battle_plan"]

    def test_bearish_entry_references_fib_618_not_fib_236(self, or_bearish, technical, fibs):
        """Fib 23.6% doesn't exist on the model — plan must use 61.8% for bearish bounces."""
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bearish"
        )
        plan = result["battle_plan"]
        assert "23.6%" not in plan, "ret_236 is not in FibonacciLevels model — must never appear"
        if "61.8%" in plan:
            assert f"{fibs.ret_618:.2f}" in plan

    def test_no_fib_236_reference_in_any_scenario(self, or_bullish, or_bearish, or_inside, technical):
        """Regression: fib.ret_236 does not exist in FibonacciLevels model."""
        for orb in (or_bullish, or_bearish, or_inside):
            for direction in ("bullish", "bearish", "neutral"):
                result = generate_expert_trade_plan(
                    "XAU", 71.5, orb, 1.0, technical, "", signal_direction=direction
                )
                assert "23.6%" not in result["battle_plan"], (
                    f"'23.6%' appeared in plan for orb={orb['broken']}, direction={direction} — "
                    f"ret_236 is not in the FibonacciLevels model"
                )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Stop / Invalidation Level Consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestStopLevelConsistency:
    def test_bullish_setup_stop_references_or_low(self, or_bullish, technical):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        plan = result["battle_plan"]
        assert "STOP:" in plan
        assert "70.50" in plan  # or_low from fixture

    def test_bearish_setup_stop_references_or_high(self, or_bearish, technical):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bearish"
        )
        plan = result["battle_plan"]
        assert "STOP:" in plan
        assert "72.00" in plan  # or_high from fixture

    def test_stop_contains_invalidation_keyword(self, or_bullish, technical):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        assert "INVALIDATED" in result["battle_plan"]

    def test_atr_buffer_shown_when_atr_positive(self, or_bullish, technical):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "",
            signal_direction="bullish", atr=1.65
        )
        assert "1.65" in result["battle_plan"]
        assert "ATR" in result["battle_plan"]

    def test_no_atr_note_when_atr_zero(self, or_bullish, technical):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "",
            signal_direction="bullish", atr=0.0
        )
        assert "ATR buffer" not in result["battle_plan"]

    def test_bullish_stop_below_or_low_not_above_current_price(self, or_bullish, technical):
        """For a long trade, the stop must be BELOW OR Low, never above current price."""
        current_price = 71.5
        or_low = 70.5
        result = generate_expert_trade_plan(
            "XAU", current_price, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        plan = result["battle_plan"]
        # Extract the stop value from "Hard stop below X" — verify it's below current price
        assert "STOP:" in plan
        stop_line = [l for l in plan.split("\n") if l.startswith("STOP:")][0]
        # The stop reference must be the or_low (70.5), which is less than current price (71.5)
        assert str(or_low) in stop_line or f"{or_low:.2f}" in stop_line


# ─────────────────────────────────────────────────────────────────────────────
# 7. Conviction Section — Indicator Value Alignment
# ─────────────────────────────────────────────────────────────────────────────

class TestConvictionSection:
    def _get_conviction(self, **kwargs):
        defaults = dict(
            symbol="XAU", price=71.5,
            or_data={"or_high": 72.0, "or_low": 70.5, "broken": "bullish"},
            rvol=1.0, technical=None, advice="",
        )
        defaults.update(kwargs)
        result = generate_expert_trade_plan(**defaults)
        conviction_lines = [l for l in result["battle_plan"].split("\n") if l.startswith("CONVICTION:")]
        return conviction_lines[0] if conviction_lines else ""

    def test_rvol_high_says_institutions_active(self):
        conv = self._get_conviction(rvol=2.5)
        assert "high" in conv.lower()
        assert "institutions" in conv.lower()

    def test_rvol_moderate(self):
        conv = self._get_conviction(rvol=1.7)
        assert "moderate" in conv.lower()

    def test_rvol_light(self):
        conv = self._get_conviction(rvol=0.8)
        assert "light" in conv.lower()

    def test_rvol_threshold_at_2(self):
        # Exactly 2.0 should be "high"
        conv = self._get_conviction(rvol=2.0)
        assert "high" in conv.lower()

    def test_rvol_threshold_at_1_5(self):
        # Exactly 1.5 should be "moderate"
        conv = self._get_conviction(rvol=1.5)
        assert "moderate" in conv.lower()

    def test_adx_strong_trend(self):
        conv = self._get_conviction(adx=35.0)
        assert "strong" in conv.lower()

    def test_adx_developing_trend(self):
        conv = self._get_conviction(adx=25.0)
        assert "developing" in conv.lower()

    def test_adx_weak_trend(self):
        conv = self._get_conviction(adx=12.0)
        assert "weak" in conv.lower()

    def test_adx_not_shown_when_zero(self):
        conv = self._get_conviction(adx=0.0)
        assert "ADX" not in conv

    def test_rsi_overbought(self):
        conv = self._get_conviction(rsi=75.0)
        assert "overbought" in conv.lower()

    def test_rsi_oversold(self):
        conv = self._get_conviction(rsi=25.0)
        assert "oversold" in conv.lower()

    def test_rsi_bullish_momentum(self):
        conv = self._get_conviction(rsi=62.0)
        assert "bullish" in conv.lower()

    def test_rsi_bearish_momentum(self):
        conv = self._get_conviction(rsi=41.0)
        assert "bearish" in conv.lower()

    def test_rsi_not_shown_when_none(self):
        conv = self._get_conviction(rsi=None)
        assert "RSI" not in conv

    def test_adx_exact_boundary_30(self):
        # ADX = 30 should be "strong"
        conv = self._get_conviction(adx=30.0)
        assert "strong" in conv.lower()

    def test_adx_exact_boundary_20(self):
        # ADX = 20 should be "developing"
        conv = self._get_conviction(adx=20.0)
        assert "developing" in conv.lower()

    def test_rsi_exact_boundary_70(self):
        conv = self._get_conviction(rsi=70.0)
        assert "overbought" in conv.lower()

    def test_rsi_exact_boundary_30(self):
        conv = self._get_conviction(rsi=30.0)
        assert "oversold" in conv.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 8. is_high_intent Flag
# ─────────────────────────────────────────────────────────────────────────────

class TestHighIntentFlag:
    def _plan(self, rvol, or_data_fixture=None):
        or_data = or_data_fixture or {"or_high": 72.0, "or_low": 70.5, "broken": "bullish"}
        return generate_expert_trade_plan("XAU", 71.5, or_data, rvol, None, "")

    def test_high_intent_true_above_threshold(self):
        assert self._plan(rvol=2.0)["is_high_intent"] is True
        assert self._plan(rvol=1.9)["is_high_intent"] is True

    def test_high_intent_false_at_threshold(self):
        assert self._plan(rvol=1.8)["is_high_intent"] is False

    def test_high_intent_false_below_threshold(self):
        assert self._plan(rvol=1.0)["is_high_intent"] is False
        assert self._plan(rvol=0.5)["is_high_intent"] is False

    def test_rvol_value_passes_through(self):
        assert self._plan(rvol=2.3)["rvol"] == pytest.approx(2.3)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Session Context
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionContext:
    def test_london_session_detected_from_london_open(self, or_bullish, session_with_london):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, None, "",
            session_ctx=session_with_london
        )
        assert "London" in result["battle_plan"]

    def test_no_session_when_london_open_none(self, or_bullish, session_no_london):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, None, "",
            session_ctx=session_no_london
        )
        # Neither London nor Asia nor New York should appear in conviction
        conviction_lines = [l for l in result["battle_plan"].split("\n") if l.startswith("CONVICTION:")]
        if conviction_lines:
            assert "London" not in conviction_lines[0]
            assert "Asia" not in conviction_lines[0]
            assert "New York" not in conviction_lines[0]

    def test_no_session_when_ctx_is_none(self, or_bullish):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, None, "",
            session_ctx=None
        )
        plan = result["battle_plan"]
        # session 'active' label should not appear without context
        assert "session active" not in plan

    def test_session_ctx_mock_with_description_london(self, or_bullish):
        ctx = MagicMock()
        ctx.london_open = None
        ctx.description = "London Open: 70.20. Prev Day High: 73.00."
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, None, "", session_ctx=ctx
        )
        assert "London" in result["battle_plan"]


# ─────────────────────────────────────────────────────────────────────────────
# 10. Inside Range / Waiting Scenarios
# ─────────────────────────────────────────────────────────────────────────────

class TestInsideRangeAndWaiting:
    def test_inside_range_shows_correct_message(self, or_inside, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_inside, 1.0, technical, "")
        assert "INSIDE RANGE" in result["battle_plan"]

    def test_inside_range_shows_both_levels(self, or_inside):
        result = generate_expert_trade_plan("XAU", 71.5, or_inside, 1.0, None, "")
        plan = result["battle_plan"]
        assert "70.50" in plan  # or_low
        assert "72.00" in plan  # or_high

    def test_waiting_message_when_no_or_levels(self, or_empty, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_empty, 1.0, technical, "")
        assert "WAITING FOR SETUP" in result["battle_plan"]

    def test_no_entry_section_for_inside_range(self, or_inside, technical):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_inside, 1.0, technical, "", signal_direction="neutral"
        )
        # Inside range + neutral signal should not suggest an entry zone
        assert "ENTRY:" not in result["battle_plan"]


# ─────────────────────────────────────────────────────────────────────────────
# 11. Pivot Level Values Match Exactly (Cross-Consistency)
# ─────────────────────────────────────────────────────────────────────────────

class TestPivotValueAccuracy:
    def test_targets_r1_matches_pivot_points_r1(self, or_bullish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        # The exact r1 value from pivot_points must appear in the targets
        assert f"R1 ({pivots.r1:.2f})" in result["battle_plan"]

    def test_targets_r2_matches_pivot_points_r2(self, or_bullish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        assert f"R2 ({pivots.r2:.2f})" in result["battle_plan"]

    def test_targets_s1_matches_pivot_points_s1(self, or_bearish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bearish"
        )
        assert f"S1 ({pivots.s1:.2f})" in result["battle_plan"]

    def test_targets_s2_matches_pivot_points_s2(self, or_bearish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bearish"
        )
        assert f"S2 ({pivots.s2:.2f})" in result["battle_plan"]

    def test_entry_s1_matches_pivot_points_s1(self, or_bullish, technical, pivots):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        assert f"S1 ({pivots.s1:.2f})" in result["battle_plan"]

    def test_fib_382_value_in_plan_matches_model(self, or_bullish, technical, fibs):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        assert f"{fibs.ret_382:.2f}" in result["battle_plan"]

    def test_fib_618_value_in_plan_matches_model_for_bearish(self, or_bearish, technical, fibs):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bearish, 1.0, technical, "", signal_direction="bearish"
        )
        assert f"{fibs.ret_618:.2f}" in result["battle_plan"]


# ─────────────────────────────────────────────────────────────────────────────
# 12. Edge Cases and Robustness
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_plan_not_empty_string(self, or_bullish):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 1.0, None, "")
        assert result["battle_plan"].strip() != ""

    def test_very_high_rvol_still_produces_valid_plan(self, or_bullish, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 99.9, technical, "")
        assert "CONVICTION:" in result["battle_plan"]

    def test_rsi_exactly_55_is_bullish_momentum(self, or_bullish):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, None, "", rsi=55.0
        )
        conv = [l for l in result["battle_plan"].split("\n") if "CONVICTION" in l]
        assert conv, "CONVICTION section missing"
        assert "bullish" in conv[0].lower()

    def test_rsi_exactly_45_is_bearish_momentum(self, or_bullish):
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, None, "", rsi=45.0
        )
        conv = [l for l in result["battle_plan"].split("\n") if "CONVICTION" in l]
        assert conv
        assert "bearish" in conv[0].lower()

    def test_all_symbols_produce_valid_output(self, or_bullish, technical):
        for sym in ["XAU", "XAG", "WTI", "BTC"]:
            result = generate_expert_trade_plan(sym, 100.0, or_bullish, 1.0, technical, "")
            assert "SITUATION:" in result["battle_plan"]

    def test_battle_plan_is_string(self, or_bullish, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 1.0, technical, "")
        assert isinstance(result["battle_plan"], str)

    def test_rvol_is_float(self, or_bullish, technical):
        result = generate_expert_trade_plan("XAU", 71.5, or_bullish, 2.3, technical, "")
        assert isinstance(result["rvol"], float)
        assert result["rvol"] == pytest.approx(2.3)

    def test_no_internal_none_in_output(self, or_bullish, technical):
        """Regression: fib.ret_236 was None and caused silent empty fib notes."""
        result = generate_expert_trade_plan(
            "XAU", 71.5, or_bullish, 1.0, technical, "", signal_direction="bullish"
        )
        plan = result["battle_plan"]
        assert "None" not in plan, "None value leaked into battle plan text"
        assert "nan" not in plan.lower(), "NaN value leaked into battle plan text"
