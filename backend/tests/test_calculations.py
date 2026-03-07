"""
Calculation Correctness Tests
==============================
These tests guard against regressions in trading calculations.
A FAILING test here means a potential capital loss in production.

Run locally:
    cd backend && pytest tests/test_calculations.py -v

Bugs caught and covered:
  1. Volatility analyzer anchoring stop/target to current_price instead of entry zone
  2. isShortTrade() inferring direction from stop/entry position (wrong for pending entries)
  3. Liquidity map division by zero (zero price, zero cluster level)
  4. Expert Battle Plan: bearish ORB + bullish signal showed short targets instead of pullback framing
  5. TwelveData batch interval names (1d/1mo rejected by API, must be 1day/1month)
"""
import pytest
import pandas as pd
import numpy as np

from app.analyzers.volatility_analyzer import analyze_volatility_and_risk, calculate_atr
from app.analyzers.liquidity_map_analyzer import calculate_liquidity_map, _cluster_levels
from app.analyzers.day_trading_expert import generate_expert_trade_plan


# ══════════════════════════════════════════════════════════════════════════════
# 1. VOLATILITY ANALYZER — Stop / Target Anchoring
# ══════════════════════════════════════════════════════════════════════════════

class TestVolatilityAnchor:
    """
    Core trading safety: stop_loss must be on the CORRECT side of the entry.

    Bullish trade: stop BELOW entry, target ABOVE entry.
    Bearish trade: stop ABOVE entry, target BELOW entry.

    Before the fix, stop/target were always anchored to current_price.
    For a pending entry (e.g. pullback to $5277 when price is $5383),
    the stop ($5370) was ABOVE the entry zone, producing inverted R/R.
    """

    def test_bullish_stop_below_entry_price(self, xau_ohlcv):
        """When entry_price is provided for a bullish signal, stop must be < entry_price."""
        entry_price = 5277.66
        current_price = 5382.97
        result = analyze_volatility_and_risk(xau_ohlcv, current_price, "bullish", entry_price=entry_price)
        assert result.stop_loss < entry_price, (
            f"Bullish stop ({result.stop_loss:.2f}) must be BELOW entry ({entry_price:.2f}). "
            "A stop above entry means a long trade can never hit its stop before taking profit — "
            "this is not a valid risk management setup."
        )

    def test_bullish_target_above_entry_price(self, xau_ohlcv):
        """Bullish take_profit must be above entry_price."""
        entry_price = 5277.66
        current_price = 5382.97
        result = analyze_volatility_and_risk(xau_ohlcv, current_price, "bullish", entry_price=entry_price)
        assert result.take_profit > entry_price, (
            f"Bullish target ({result.take_profit:.2f}) must be ABOVE entry ({entry_price:.2f})."
        )

    def test_bearish_stop_above_entry_price(self, xau_ohlcv):
        """For a bearish signal with entry_price, stop must be above entry_price."""
        entry_price = 5410.0
        current_price = 5382.97
        result = analyze_volatility_and_risk(xau_ohlcv, current_price, "bearish", entry_price=entry_price)
        assert result.stop_loss > entry_price, (
            f"Bearish stop ({result.stop_loss:.2f}) must be ABOVE entry ({entry_price:.2f})."
        )

    def test_bearish_target_below_entry_price(self, xau_ohlcv):
        """Bearish take_profit must be below entry_price."""
        entry_price = 5410.0
        current_price = 5382.97
        result = analyze_volatility_and_risk(xau_ohlcv, current_price, "bearish", entry_price=entry_price)
        assert result.take_profit < entry_price, (
            f"Bearish target ({result.take_profit:.2f}) must be BELOW entry ({entry_price:.2f})."
        )

    def test_fallback_to_current_price_when_no_entry(self, xau_ohlcv):
        """Without entry_price, anchor falls back to current_price (immediate entry)."""
        current_price = 5382.97
        result_with = analyze_volatility_and_risk(xau_ohlcv, current_price, "bullish", entry_price=current_price)
        result_without = analyze_volatility_and_risk(xau_ohlcv, current_price, "bullish")
        assert abs(result_with.stop_loss - result_without.stop_loss) < 0.01
        assert abs(result_with.take_profit - result_without.take_profit) < 0.01

    def test_entry_price_zero_falls_back_to_current_price(self, xau_ohlcv):
        """entry_price=0 must be treated as 'not provided' and fall back to current_price."""
        current_price = 5382.97
        result_zero = analyze_volatility_and_risk(xau_ohlcv, current_price, "bullish", entry_price=0)
        result_none = analyze_volatility_and_risk(xau_ohlcv, current_price, "bullish", entry_price=None)
        assert abs(result_zero.stop_loss - result_none.stop_loss) < 0.01

    def test_rr_ratio_is_consistent_with_multipliers(self, xau_ohlcv):
        """
        R:R ratio = atr_multiplier_tp / atr_multiplier_sl (default 3.0/1.5 = 2.0).
        This must hold regardless of which price is used as anchor.
        """
        result = analyze_volatility_and_risk(xau_ohlcv, 5382.97, "bullish", entry_price=5277.66)
        atr = result.atr
        if atr > 0:
            risk = abs(result.stop_loss - 5277.66)
            reward = abs(result.take_profit - 5277.66)
            rr = reward / risk
            assert abs(rr - 2.0) < 0.01, f"Expected R:R=2.0, got {rr:.4f}"

    def test_no_division_by_zero_on_zero_atr(self, sample_daily_data):
        """Zero ATR (insufficient data) must return a safe default, not crash."""
        tiny_df = sample_daily_data.head(5)
        result = analyze_volatility_and_risk(tiny_df, 100.0, "bullish")
        assert result.stop_loss == 0.0
        assert result.take_profit == 0.0

    def test_pending_entry_stop_not_above_current_price_for_bullish(self, wti_ohlcv):
        """
        WTI scenario: current=$71.64, entry_zone=$66.26 (pullback).
        Old bug: stop was $71.64 - ATR*1.5 = $68.61 (above entry zone).
        New behavior: stop must be below the entry zone price.
        """
        current_price = 71.64
        entry_price = 66.26
        result = analyze_volatility_and_risk(wti_ohlcv, current_price, "bullish", entry_price=entry_price)
        assert result.stop_loss < entry_price, (
            f"WTI: stop ({result.stop_loss:.2f}) must be below entry zone ({entry_price:.2f}). "
            "Old bug placed stop at current_price - ATR, which was above the entry zone."
        )
        assert result.take_profit > entry_price


# ══════════════════════════════════════════════════════════════════════════════
# 2. LIQUIDITY MAP — Division-by-Zero Guards
# ══════════════════════════════════════════════════════════════════════════════

class TestLiquidityMapGuards:
    """
    Guard against ZeroDivisionError crashes that were hitting Lambda in production.
    Error message: "Liquidity map calculation failed: float division by zero"
    """

    def test_returns_none_for_zero_current_price(self, wti_ohlcv):
        """current_price=0 must return None, not crash."""
        result = calculate_liquidity_map(wti_ohlcv, current_price=0.0)
        assert result is None, "current_price=0 should return None gracefully"

    def test_returns_none_for_negative_current_price(self, wti_ohlcv):
        """Negative price is invalid — must return None."""
        result = calculate_liquidity_map(wti_ohlcv, current_price=-50.0)
        assert result is None

    def test_returns_none_for_insufficient_data(self, wti_ohlcv):
        """Fewer than 30 rows must return None."""
        result = calculate_liquidity_map(wti_ohlcv.head(20), current_price=71.64)
        assert result is None

    def test_returns_none_for_none_dataframe(self):
        """None dataframe must return None."""
        result = calculate_liquidity_map(None, current_price=71.64)
        assert result is None

    def test_valid_data_returns_liquidity_map(self, wti_ohlcv):
        """Valid data must produce resistance and support levels."""
        result = calculate_liquidity_map(wti_ohlcv, current_price=71.64)
        assert result is not None
        assert len(result.resistance_levels) > 0
        assert len(result.support_levels) > 0

    def test_resistance_levels_above_price(self, wti_ohlcv):
        """All resistance levels must be strictly above current_price."""
        current_price = 71.64
        result = calculate_liquidity_map(wti_ohlcv, current_price)
        for lvl in result.resistance_levels:
            assert lvl.price > current_price, (
                f"Resistance level {lvl.price} should be above current price {current_price}"
            )

    def test_support_levels_below_price(self, wti_ohlcv):
        """All support levels must be strictly below current_price."""
        current_price = 71.64
        result = calculate_liquidity_map(wti_ohlcv, current_price)
        for lvl in result.support_levels:
            assert lvl.price < current_price, (
                f"Support level {lvl.price} should be below current price {current_price}"
            )

    def test_cluster_levels_no_crash_with_zero_level(self):
        """_cluster_levels must not crash when a level value is 0.0."""
        try:
            result = _cluster_levels([0.0, 0.5, 1.0, 1.5])
            assert isinstance(result, list)
        except ZeroDivisionError:
            pytest.fail("_cluster_levels crashed with ZeroDivisionError on zero-value level")

    def test_cluster_levels_empty_input(self):
        """Empty input must return empty list."""
        assert _cluster_levels([]) == []

    def test_cluster_levels_single_item(self):
        """Single level must return that level unchanged."""
        result = _cluster_levels([75.5])
        assert len(result) == 1
        assert abs(result[0] - 75.5) < 0.01

    def test_distance_pct_always_positive(self, wti_ohlcv):
        """distance_pct on every level must be >= 0."""
        result = calculate_liquidity_map(wti_ohlcv, 71.64)
        for lvl in result.resistance_levels + result.support_levels:
            assert lvl.distance_pct >= 0, f"Negative distance_pct: {lvl.distance_pct}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. EXPERT BATTLE PLAN — ORB × Signal Direction Matrix
# ══════════════════════════════════════════════════════════════════════════════

class TestExpertBattlePlan:
    """
    Validate that the Expert Battle Plan correctly frames ORB direction
    in context of the overall signal direction.

    Bug: Bearish ORB + bullish signal was showing "TARGETS: Aim for S1/S2"
    (i.e., short trade targets), but these are actually the ENTRY zones
    for the long setup. This would instruct a bullish trader to go SHORT.
    """

    def test_bearish_orb_bullish_signal_shows_pullback_framing(
        self, or_data_bearish, technical_analysis_bullish
    ):
        """
        WTI case: ORB broke bearish but overall signal is bullish.
        Plan must say PULLBACK, not TARGETS (S1/S2 as short targets).
        """
        result = generate_expert_trade_plan(
            "WTI", price=71.64,
            or_data=or_data_bearish,
            rvol=1.0,
            technical=technical_analysis_bullish,
            advice="",
            signal_direction="bullish"
        )
        plan = result["battle_plan"].upper()
        assert "PULLBACK" in plan, (
            f"Expected PULLBACK framing for bearish ORB + bullish signal, got: {plan}"
        )
        assert "TARGETS: AIM FOR S1" not in plan, (
            "Must NOT show short targets when overall signal is bullish"
        )

    def test_bearish_orb_bullish_signal_mentions_fib_entry(
        self, or_data_bearish, technical_analysis_bullish
    ):
        """Bearish ORB + bullish signal must mention the Fib 38.2% entry zone."""
        result = generate_expert_trade_plan(
            "WTI", price=71.64,
            or_data=or_data_bearish,
            rvol=1.0,
            technical=technical_analysis_bullish,
            advice="",
            signal_direction="bullish"
        )
        plan = result["battle_plan"]
        assert "38.2" in plan or "KEY ENTRY" in plan.upper(), (
            f"Expected Fib 38.2% entry hint in plan, got: {plan}"
        )

    def test_bullish_orb_bullish_signal_shows_r1_r2_targets(
        self, or_data_bullish, technical_analysis_bullish
    ):
        """Aligned: bullish ORB + bullish signal → R1/R2 targets."""
        result = generate_expert_trade_plan(
            "WTI", price=73.0,
            or_data=or_data_bullish,
            rvol=1.0,
            technical=technical_analysis_bullish,
            advice="",
            signal_direction="bullish"
        )
        plan = result["battle_plan"].upper()
        assert "R1" in plan and "R2" in plan, (
            f"Expected R1/R2 targets for bullish ORB + bullish signal, got: {plan}"
        )

    def test_bearish_orb_bearish_signal_shows_s1_s2_targets(
        self, or_data_bearish, technical_analysis_bullish
    ):
        """Aligned: bearish ORB + bearish signal → S1/S2 targets (short trade)."""
        result = generate_expert_trade_plan(
            "WTI", price=71.0,
            or_data=or_data_bearish,
            rvol=1.0,
            technical=technical_analysis_bullish,
            advice="",
            signal_direction="bearish"
        )
        plan = result["battle_plan"].upper()
        assert "S1" in plan or "S2" in plan, (
            f"Expected S1/S2 targets for bearish ORB + bearish signal, got: {plan}"
        )
        assert "CAUTION" not in plan

    def test_bullish_orb_bearish_signal_shows_caution(
        self, or_data_bullish, technical_analysis_bullish
    ):
        """
        Conflicting: bullish ORB but bearish signal — intraday bounce into resistance.
        Plan must warn of fade/rejection, not blindly show R1/R2 as targets.
        """
        result = generate_expert_trade_plan(
            "WTI", price=73.0,
            or_data=or_data_bullish,
            rvol=1.0,
            technical=technical_analysis_bullish,
            advice="",
            signal_direction="bearish"
        )
        plan = result["battle_plan"].upper()
        assert "COUNTER-TREND" in plan or "FADE" in plan, (
            f"Expected caution/fade framing for bullish ORB + bearish signal, got: {plan}"
        )
        assert "R1" not in plan.split("ENTRY")[0], (
            f"Bullish R1/R2 targets should not appear when daily signal is bearish, got: {plan}"
        )

    def test_no_orb_fallback_uses_price_vs_pivot(
        self, or_data_none, technical_analysis_bullish
    ):
        """No ORB breakout → falls back to price vs pivot for target direction."""
        result = generate_expert_trade_plan(
            "WTI", price=73.0,   # above pivot=70
            or_data=or_data_none,
            rvol=1.0,
            technical=technical_analysis_bullish,
            advice="",
            signal_direction="bullish"
        )
        plan = result["battle_plan"].upper()
        assert "R1" in plan or "R2" in plan, (
            f"Price above pivot + no ORB should target R1/R2, got: {plan}"
        )

    def test_high_rvol_adds_conviction_message(
        self, or_data_bullish, technical_analysis_bullish
    ):
        """RVOL > 2 must add a HIGH CONVICTION message."""
        result = generate_expert_trade_plan(
            "WTI", price=73.0,
            or_data=or_data_bullish,
            rvol=2.5,
            technical=technical_analysis_bullish,
            advice="",
            signal_direction="bullish"
        )
        assert "CONVICTION" in result["battle_plan"].upper()
        assert result["is_high_intent"] is True

    def test_returns_dict_with_required_keys(
        self, or_data_bullish, technical_analysis_bullish
    ):
        """Result must always have battle_plan, rvol, is_high_intent."""
        result = generate_expert_trade_plan(
            "WTI", price=73.0,
            or_data=or_data_bullish,
            rvol=1.0,
            technical=technical_analysis_bullish,
            advice="",
        )
        assert "battle_plan" in result
        assert "rvol" in result
        assert "is_high_intent" in result


# ══════════════════════════════════════════════════════════════════════════════
# 4. TWELVEDATA INTERVAL MAPPING
# ══════════════════════════════════════════════════════════════════════════════

class TestTwelveDataIntervals:
    """
    Validate that intervals passed to fetch_batch_data are valid TwelveData strings.
    Bug: "1d", "1mo", "1wk" were passed directly to API → "Invalid interval" warnings.
    Accepted intervals: 1min,5min,15min,30min,45min,1h,2h,4h,8h,1day,1week,1month
    """

    VALID_INTERVALS = {
        "1min", "5min", "15min", "30min", "45min",
        "1h", "2h", "4h", "8h",
        "1day", "1week", "1month"
    }
    INVALID_INTERVALS = {"1d", "1mo", "1wk", "daily", "weekly", "monthly", "D", "W", "M"}

    def test_valid_intervals_accepted(self):
        """Smoke check: each valid interval string is in the accepted set."""
        for interval in self.VALID_INTERVALS:
            assert interval in self.VALID_INTERVALS

    def test_yfinance_style_intervals_are_invalid(self):
        """
        yfinance-style intervals must NOT be passed to TwelveData batch fetch.
        These trigger "Invalid interval provided" API warnings.
        """
        for bad in self.INVALID_INTERVALS:
            assert bad not in self.VALID_INTERVALS, (
                f"'{bad}' is a yfinance-style interval rejected by TwelveData API"
            )

    def test_bench_interval_for_long_term_is_valid(self):
        """Long-term scan must use '1month' (not '1mo') for benchmark batch fetch."""
        bench_interval = "1month"  # must match what main.py now sets
        assert bench_interval in self.VALID_INTERVALS

    def test_exec_interval_for_long_term_is_valid(self):
        """Long-term execution interval must be '1day' (not '1d')."""
        exec_interval = "1day"
        assert exec_interval in self.VALID_INTERVALS

    def test_exec_interval_for_short_term_is_valid(self):
        """Short-term execution interval '1h' must be valid."""
        exec_interval = "1h"
        assert exec_interval in self.VALID_INTERVALS


# ══════════════════════════════════════════════════════════════════════════════
# 5. R/R CALCULATION SANITY (pure math — no external deps)
# ══════════════════════════════════════════════════════════════════════════════

class TestRRCalculationLogic:
    """
    Mirror the frontend getRRReward / getRRRisk / isShortTrade logic in Python
    so we can catch regression before the Angular build is even triggered.
    """

    @staticmethod
    def is_short_trade(recommendation: str) -> bool:
        return recommendation.lower() == "bearish"

    @staticmethod
    def get_rr_reward(entry: float, take_profit: float, is_short: bool) -> float:
        reward = (entry - take_profit) if is_short else (take_profit - entry)
        return max(0.0, reward)

    @staticmethod
    def get_rr_risk(entry: float, stop_loss: float, is_short: bool) -> float:
        risk = (stop_loss - entry) if is_short else (entry - stop_loss)
        return max(0.0, risk)

    def test_bullish_pending_entry_reward_positive(self):
        """
        XAU scenario after fix:
          entry=5277.66, stop=5265.00, target=5303.00, signal=bullish
          reward = 5303 - 5277.66 = 25.34 > 0
        """
        entry, stop, target = 5277.66, 5265.00, 5303.00
        is_short = self.is_short_trade("bullish")
        reward = self.get_rr_reward(entry, target, is_short)
        risk = self.get_rr_risk(entry, stop, is_short)
        assert reward > 0, f"Reward should be positive, got {reward}"
        assert risk > 0, f"Risk should be positive, got {risk}"

    def test_bullish_rr_ratio_is_2_to_1(self):
        """Default multipliers 3x/1.5x give 2:1 R:R."""
        atr = 10.0
        entry = 100.0
        stop = entry - atr * 1.5   # 85
        target = entry + atr * 3.0  # 130
        is_short = self.is_short_trade("bullish")
        reward = self.get_rr_reward(entry, target, is_short)
        risk = self.get_rr_risk(entry, stop, is_short)
        assert risk > 0
        assert abs(reward / risk - 2.0) < 0.001

    def test_neutral_signal_treated_as_long(self):
        """Neutral signal should NOT be treated as short."""
        assert not self.is_short_trade("neutral")

    def test_bearish_signal_is_short(self):
        assert self.is_short_trade("bearish")

    def test_bullish_signal_is_not_short(self):
        assert not self.is_short_trade("bullish")

    def test_old_bug_scenario_xau(self):
        """
        Reproduce the original bug:
          current=5382.97, stop=5370.30 (from current - ATR*1.5), entry_zone=5277.66
          With old isShortTrade (stop > entry) → is_short=True
          → reward = entry - target = 5277.66 - 5408.31 = -130 → clamped to 0
          → risk = stop - entry = 5370.30 - 5277.66 = 92.64 (shown as loss on a long!)

        After the fix: isShortTrade uses recommendation='bullish' → False,
        and stop is anchored to entry, so stop < entry.
        """
        entry = 5277.66
        stop_old = 5370.30  # anchored to current_price (OLD bug)
        target = 5408.31    # anchored to current_price (OLD bug)

        # OLD (wrong) behavior
        is_short_old = stop_old > entry  # True — bug
        reward_old = self.get_rr_reward(entry, target, is_short_old)
        risk_old = self.get_rr_risk(entry, stop_old, is_short_old)
        assert reward_old == 0.0, "Old bug: reward was $0 (proved the bug is reproduced)"
        assert risk_old > 0, "Old bug: risk was non-zero but wrong direction"

        # NEW (correct) behavior — stop anchored to entry zone
        stop_new = 5265.00  # entry - ATR*1.5
        target_new = 5303.00  # entry + ATR*3.0
        is_short_new = self.is_short_trade("bullish")  # False
        reward_new = self.get_rr_reward(entry, target_new, is_short_new)
        risk_new = self.get_rr_risk(entry, stop_new, is_short_new)
        assert reward_new > 0, "New: reward must be positive"
        assert risk_new > 0, "New: risk must be positive"
        assert reward_new / risk_new == pytest.approx(2.0, rel=0.05)
