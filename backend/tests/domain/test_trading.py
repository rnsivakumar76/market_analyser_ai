"""
Comprehensive unit tests for domain/trading/.

Tests cover: RVOL, Opening Range Breakout, and Position Sizing.
All tests use primitive types only — no Pydantic models, no pandas.
"""

import pytest

from domain.trading.rvol import calculate_rvol, classify_rvol, is_high_intent
from domain.trading.opening_range import detect_opening_range, ORBData, classify_orb_context
from domain.trading.position_sizer import (
    calculate_correlation_penalty,
    calculate_risk_amount,
    calculate_risk_per_unit,
    calculate_position_units,
)
from domain.constants import (
    RVOL_HIGH, RVOL_MODERATE, RVOL_HIGH_INTENT,
    POSITION_CORRELATION_FLOOR,
    POSITION_CORRELATION_MAX_PENALTY,
)


# ═══════════════════════════════════════════════════════════════════════════
# RVOL Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRVOL:

    def test_rvol_returns_float(self):
        result = calculate_rvol(2000.0, [1000.0, 1000.0, 1000.0])
        assert isinstance(result, float)

    def test_rvol_double_average_gives_two(self):
        """Current volume = 2x average → RVOL = 2.0"""
        result = calculate_rvol(2000.0, [1000.0, 1000.0, 1000.0])
        assert result == pytest.approx(2.0, abs=0.01)

    def test_rvol_half_average_gives_half(self):
        result = calculate_rvol(500.0, [1000.0, 1000.0, 1000.0])
        assert result == pytest.approx(0.5, abs=0.01)

    def test_rvol_same_as_average_gives_one(self):
        result = calculate_rvol(1000.0, [1000.0, 1000.0, 1000.0])
        assert result == pytest.approx(1.0, abs=0.01)

    def test_rvol_no_history_returns_one(self):
        result = calculate_rvol(1000.0, [])
        assert result == 1.0

    def test_rvol_zero_average_returns_one(self):
        result = calculate_rvol(1000.0, [0.0, 0.0, 0.0])
        assert result == 1.0

    def test_rvol_rounded_to_two_dp(self):
        result = calculate_rvol(1234.0, [1000.0])
        # 1234 / 1000 = 1.234 → rounds to 1.23
        assert result == pytest.approx(1.23, abs=0.005)

    def test_rvol_nan_history_ignored(self):
        import numpy as np
        result = calculate_rvol(2000.0, [1000.0, float('nan'), 1000.0])
        assert result == pytest.approx(2.0, abs=0.01)

    def test_classify_rvol_high(self):
        assert classify_rvol(RVOL_HIGH) == "high"

    def test_classify_rvol_moderate(self):
        assert classify_rvol(RVOL_MODERATE) == "moderate"

    def test_classify_rvol_light(self):
        assert classify_rvol(1.0) == "light"

    def test_classify_rvol_above_high(self):
        assert classify_rvol(3.0) == "high"

    def test_is_high_intent_true(self):
        assert is_high_intent(RVOL_HIGH_INTENT + 0.1) is True

    def test_is_high_intent_false_at_threshold(self):
        assert is_high_intent(RVOL_HIGH_INTENT) is False

    def test_is_high_intent_false_below(self):
        assert is_high_intent(1.0) is False


# ═══════════════════════════════════════════════════════════════════════════
# Opening Range Breakout Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestOpeningRangeBreakout:

    def test_orb_returns_dataclass(self):
        result = detect_opening_range([105.0], [95.0], current_price=100.0)
        assert isinstance(result, ORBData)

    def test_orb_bullish_breakout(self):
        result = detect_opening_range([105.0], [95.0], current_price=106.0)
        assert result.broken == "bullish"
        assert result.or_high == 105.0
        assert result.or_low == 95.0

    def test_orb_bearish_breakout(self):
        result = detect_opening_range([105.0], [95.0], current_price=93.0)
        assert result.broken == "bearish"

    def test_orb_inside_range(self):
        result = detect_opening_range([105.0], [95.0], current_price=100.0)
        assert result.broken == "none"

    def test_orb_exactly_at_high_is_bullish(self):
        result = detect_opening_range([105.0], [95.0], current_price=105.01)
        assert result.broken == "bullish"

    def test_orb_exactly_at_low_is_bearish(self):
        result = detect_opening_range([105.0], [95.0], current_price=94.99)
        assert result.broken == "bearish"

    def test_orb_empty_session_returns_empty(self):
        result = detect_opening_range([], [], current_price=100.0)
        assert result.or_high == 0.0
        assert result.or_low == 0.0
        assert result.broken == "none"

    def test_orb_custom_opening_bar_index(self):
        highs = [105.0, 108.0, 110.0]
        lows = [95.0, 98.0, 100.0]
        result = detect_opening_range(highs, lows, current_price=109.0, opening_bar_index=1)
        assert result.or_high == pytest.approx(108.0, abs=0.01)
        assert result.or_low == pytest.approx(98.0, abs=0.01)
        assert result.broken == "bullish"

    def test_orb_index_out_of_range_returns_empty(self):
        result = detect_opening_range([105.0], [95.0], current_price=100.0, opening_bar_index=5)
        assert result.broken == "none"

    # classify_orb_context
    def test_classify_aligned_bullish(self):
        orb = ORBData(or_high=105.0, or_low=95.0, broken="bullish")
        assert classify_orb_context(orb, "bullish") == "aligned_bullish"

    def test_classify_aligned_bearish(self):
        orb = ORBData(or_high=105.0, or_low=95.0, broken="bearish")
        assert classify_orb_context(orb, "bearish") == "aligned_bearish"

    def test_classify_counter_bull_orb(self):
        orb = ORBData(or_high=105.0, or_low=95.0, broken="bullish")
        assert classify_orb_context(orb, "bearish") == "counter_bull_orb"

    def test_classify_counter_bear_orb(self):
        orb = ORBData(or_high=105.0, or_low=95.0, broken="bearish")
        assert classify_orb_context(orb, "bullish") == "counter_bear_orb"

    def test_classify_inside_range(self):
        orb = ORBData(or_high=105.0, or_low=95.0, broken="none")
        assert classify_orb_context(orb, "bullish") == "inside_range"

    def test_orb_degenerate_single_candle_flat_bar(self):
        """Regression: when the first bar is flat (high == low == close), or_high == or_low.
        domain must return broken='none' so the battle plan shows WAITING FOR SETUP, not
        INSIDE RANGE — Price is consolidating between OR Low (84.37) and OR High (84.37)."""
        price = 84.37
        result = detect_opening_range([price], [price], current_price=price)
        assert result.or_high == pytest.approx(84.37)
        assert result.or_low == pytest.approx(84.37)
        assert result.broken == "none"

    def test_orb_degenerate_range_is_not_a_breakout(self):
        """A price exactly equal to a degenerate (flat) range must not trigger bullish/bearish."""
        price = 100.0
        result = detect_opening_range([price], [price], current_price=price)
        assert result.broken == "none"


# ═══════════════════════════════════════════════════════════════════════════
# Position Sizer Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPositionSizer:

    # ── Correlation Penalty ──────────────────────────────────────────────

    def test_no_penalty_below_floor(self):
        penalty = calculate_correlation_penalty(0.2)
        assert penalty == 0.0

    def test_no_penalty_at_floor(self):
        penalty = calculate_correlation_penalty(POSITION_CORRELATION_FLOOR)
        assert penalty == 0.0

    def test_penalty_above_floor(self):
        penalty = calculate_correlation_penalty(0.6)
        assert penalty > 0.0

    def test_penalty_capped_at_max(self):
        penalty = calculate_correlation_penalty(1.0)
        assert penalty == pytest.approx(POSITION_CORRELATION_MAX_PENALTY, abs=0.001)

    def test_penalty_linear_between_floor_and_max(self):
        p1 = calculate_correlation_penalty(0.5)
        p2 = calculate_correlation_penalty(0.7)
        assert p2 > p1

    def test_penalty_zero_correlation_no_penalty(self):
        penalty = calculate_correlation_penalty(0.0)
        assert penalty == 0.0

    # ── Risk Amount ──────────────────────────────────────────────────────

    def test_risk_amount_no_penalty(self):
        amount = calculate_risk_amount(
            portfolio_value=100_000.0,
            base_risk_percent=1.0,
            penalty_factor=0.0,
        )
        assert amount == pytest.approx(1000.0, abs=0.01)

    def test_risk_amount_50_pct_penalty(self):
        amount = calculate_risk_amount(
            portfolio_value=100_000.0,
            base_risk_percent=1.0,
            penalty_factor=0.5,
        )
        assert amount == pytest.approx(500.0, abs=0.01)

    def test_risk_amount_full_penalty_zero(self):
        amount = calculate_risk_amount(
            portfolio_value=100_000.0,
            base_risk_percent=1.0,
            penalty_factor=1.0,
        )
        assert amount == pytest.approx(0.0, abs=0.01)

    def test_risk_amount_scales_with_portfolio(self):
        a1 = calculate_risk_amount(50_000.0, 1.0, 0.0)
        a2 = calculate_risk_amount(100_000.0, 1.0, 0.0)
        assert a2 == pytest.approx(a1 * 2, abs=0.01)

    # ── Risk Per Unit ─────────────────────────────────────────────────────

    def test_risk_per_unit_normal(self):
        risk = calculate_risk_per_unit(entry_price=100.0, stop_loss=95.0, atr=2.0)
        assert risk == pytest.approx(5.0, abs=0.001)

    def test_risk_per_unit_short_trade(self):
        """Short trade: entry 100, SL 105 → risk = 5"""
        risk = calculate_risk_per_unit(entry_price=100.0, stop_loss=105.0, atr=2.0)
        assert risk == pytest.approx(5.0, abs=0.001)

    def test_risk_per_unit_fallback_when_sl_equals_entry(self):
        """When SL ≈ entry, fall back to ATR × 1.5"""
        risk = calculate_risk_per_unit(entry_price=100.0, stop_loss=100.0, atr=2.0)
        assert risk == pytest.approx(3.0, abs=0.001)

    def test_risk_per_unit_always_positive(self):
        risk = calculate_risk_per_unit(entry_price=95.0, stop_loss=100.0, atr=2.0)
        assert risk > 0.0

    # ── Full Position Sizing ──────────────────────────────────────────────

    def test_position_units_returns_tuple(self):
        result = calculate_position_units(
            portfolio_value=100_000.0,
            base_risk_percent=1.0,
            entry_price=100.0,
            stop_loss=95.0,
            atr=2.0,
        )
        assert len(result) == 4

    def test_position_units_basic_calculation(self):
        """$100k, 1% risk, $5 risk/unit → 200 units."""
        units, risk_amt, penalty, final_pct = calculate_position_units(
            portfolio_value=100_000.0,
            base_risk_percent=1.0,
            entry_price=100.0,
            stop_loss=95.0,
            atr=2.0,
            avg_correlation=0.0,
        )
        assert units == pytest.approx(200.0, abs=1.0)
        assert risk_amt == pytest.approx(1000.0, abs=0.01)
        assert penalty == 0.0
        assert final_pct == pytest.approx(1.0, abs=0.01)

    def test_position_units_reduced_by_correlation(self):
        units_no_corr, _, _, _ = calculate_position_units(
            100_000.0, 1.0, 100.0, 95.0, 2.0, avg_correlation=0.0
        )
        units_high_corr, _, _, _ = calculate_position_units(
            100_000.0, 1.0, 100.0, 95.0, 2.0, avg_correlation=0.9
        )
        assert units_high_corr < units_no_corr

    def test_position_units_rounded_appropriately(self):
        units, _, _, _ = calculate_position_units(
            10_000.0, 1.0, 100.0, 99.0, 1.0, avg_correlation=0.0
        )
        # risk_per_unit=1, risk_amount=100 → 100 units (integer)
        assert units == 100.0
        assert isinstance(units, float)

    def test_position_units_zero_when_no_risk_per_unit(self):
        units, _, _, _ = calculate_position_units(
            100_000.0, 1.0,
            entry_price=100.0,
            stop_loss=100.0,  # SL=entry, ATR=0 → fallback=0
            atr=0.0,
        )
        assert units == 0.0

    def test_position_sizing_penalty_factor_in_output(self):
        _, _, penalty, final_pct = calculate_position_units(
            100_000.0, 1.0, 100.0, 95.0, 2.0, avg_correlation=0.8
        )
        assert penalty > 0.0
        assert final_pct < 1.0

    def test_position_units_small_account_precision(self):
        """Small account should give decimal units rather than 0."""
        units, _, _, _ = calculate_position_units(
            5_000.0, 1.0, 100.0, 99.0, 1.0
        )
        # risk=50, risk_per_unit=1 → 50 units
        assert units == pytest.approx(50.0, abs=1.0)
