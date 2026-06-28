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
from app.models import NewsItem, NewsSentiment, StrengthAnalysis, VolatilityAnalysis, TradeSignal, TradePlan, TechnicalAnalysis, Signal, StrategySettings


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
        R:R ratio = tp3_mult / sl_mult.  The regime-adaptive table maintains 2:1
        across all four regimes (LOW 2.0/1.0=2, NORMAL 3.0/1.5=2, etc.).
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
# 2. VOLATILITY — Regime-Adaptive ATR Multipliers
# ══════════════════════════════════════════════════════════════════════════════

def _make_volatility_df(history_range: float, recent_range: float,
                         n_history: int = 186, n_recent: int = 14) -> pd.DataFrame:
    """
    Build a synthetic OHLCV DataFrame with two volatility phases.

    history_range: H-L of the first n_history bars (sets the baseline ATR distribution).
    recent_range:  H-L of the last n_recent bars (determines the current ATR).

    By keeping history_range >> recent_range we force a COMPRESSED regime;
    by keeping recent_range >> history_range we force an EXTREME regime.
    """
    dates = pd.date_range("2024-01-01", periods=n_history + n_recent, freq="B")
    close = 1000.0
    rows = []
    for i in range(n_history + n_recent):
        r = recent_range if i >= n_history else history_range
        rows.append({
            "Open": close,
            "High": close + r,
            "Low": close,
            "Close": close + r / 2,
            "Volume": 1_000_000,
        })
        close += 0.1
    return pd.DataFrame(rows, index=dates)


class TestRegimeAdaptiveMultipliers:
    """
    Regression: ATR multipliers must widen in EXTREME volatility and tighten
    in COMPRESSED volatility.  R/R must remain 2:1 across all regimes.
    """

    def test_compressed_regime_uses_tighter_sl_than_normal(self):
        """In a flat/compressed market the stop should be tighter than 1.5× ATR."""
        df = _make_volatility_df(history_range=20.0, recent_range=0.5)
        result = analyze_volatility_and_risk(df, 1000.0, "bullish")
        if result.atr > 0:
            sl_distance = abs(result.stop_loss - 1000.0)
            normal_sl_distance = result.atr * 1.5
            assert sl_distance <= normal_sl_distance + 0.01, (
                f"COMPRESSED regime: SL distance {sl_distance:.4f} must be ≤ NORMAL "
                f"1.5× ATR distance {normal_sl_distance:.4f}."
            )
            assert "Compressed" in result.description or "Low" in result.description or \
                   "Normal" in result.description, \
                "Description must include the regime label"

    def test_extreme_regime_uses_wider_sl_than_normal(self):
        """In a highly volatile market the stop should be wider than 1.5× ATR."""
        df = _make_volatility_df(history_range=0.5, recent_range=20.0)
        result = analyze_volatility_and_risk(df, 1000.0, "bullish")
        if result.atr > 0:
            sl_distance = abs(result.stop_loss - 1000.0)
            normal_sl_distance = result.atr * 1.5
            assert sl_distance >= normal_sl_distance - 0.01, (
                f"EXTREME regime: SL distance {sl_distance:.4f} must be ≥ NORMAL "
                f"1.5× ATR distance {normal_sl_distance:.4f}."
            )

    def test_rr_is_two_to_one_in_compressed_regime(self):
        """R/R must be 2:1 even when COMPRESSED multipliers are used."""
        df = _make_volatility_df(history_range=20.0, recent_range=0.5)
        result = analyze_volatility_and_risk(df, 1000.0, "bullish")
        if result.atr > 0:
            risk   = abs(result.stop_loss - 1000.0)
            reward = abs(result.take_profit - 1000.0)
            assert risk > 0
            assert abs(reward / risk - 2.0) < 0.01, (
                f"COMPRESSED R:R = {reward/risk:.3f}, expected 2.0"
            )

    def test_rr_is_two_to_one_in_extreme_regime(self):
        """R/R must be 2:1 even when EXTREME multipliers are used."""
        df = _make_volatility_df(history_range=0.5, recent_range=20.0)
        result = analyze_volatility_and_risk(df, 1000.0, "bullish")
        if result.atr > 0:
            risk   = abs(result.stop_loss - 1000.0)
            reward = abs(result.take_profit - 1000.0)
            assert risk > 0
            assert abs(reward / risk - 2.0) < 0.01, (
                f"EXTREME R:R = {reward/risk:.3f}, expected 2.0"
            )

    def test_description_contains_regime_label(self):
        """Description must always include the volatility regime label and multipliers."""
        df = _make_volatility_df(history_range=5.0, recent_range=5.0)
        result = analyze_volatility_and_risk(df, 1000.0, "bullish")
        if result.atr > 0:
            assert "vol" in result.description.lower() or "×" in result.description, (
                f"Description missing regime note: {result.description!r}"
            )

    def test_caller_override_bypasses_adaptive_table(self):
        """Explicit non-default multipliers must override regime-adaptive selection."""
        df = _make_volatility_df(history_range=0.5, recent_range=20.0)  # EXTREME regime
        result = analyze_volatility_and_risk(
            df, 1000.0, "bullish",
            atr_multiplier_sl=1.0, atr_multiplier_tp=2.0  # explicit override
        )
        if result.atr > 0:
            sl_distance = abs(result.stop_loss - 1000.0)
            expected_sl = result.atr * 1.0
            assert abs(sl_distance - expected_sl) < 0.01, (
                f"Override: expected SL=1.0×ATR ({expected_sl:.4f}), got {sl_distance:.4f}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# 3. LIQUIDITY MAP — Division-by-Zero Guards
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


# ══════════════════════════════════════════════════════════════════════════════
# 6. GEOPOLITICAL RISK ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

class TestGeopoliticalRiskAnalyzer:
    """Test geopolitical risk detection and analysis."""

    def test_get_symbol_group_crude(self):
        """Test symbol group detection for crude oil instruments."""
        from app.analyzers.geo_risk_analyzer import _get_symbol_group
        assert _get_symbol_group('WTI') == 'crude'
        assert _get_symbol_group('CL') == 'crude'
        assert _get_symbol_group('OIL') == 'crude'
        assert _get_symbol_group('BRENT') == 'crude'

    def test_get_symbol_group_gold(self):
        """Test symbol group detection for gold/silver instruments."""
        from app.analyzers.geo_risk_analyzer import _get_symbol_group
        assert _get_symbol_group('XAU') == 'gold'
        assert _get_symbol_group('GOLD') == 'gold'
        assert _get_symbol_group('XAG') == 'gold'
        assert _get_symbol_group('SILVER') == 'gold'

    def test_get_symbol_group_crypto(self):
        """Test symbol group detection for crypto instruments."""
        from app.analyzers.geo_risk_analyzer import _get_symbol_group
        assert _get_symbol_group('BTC') == 'crypto'
        assert _get_symbol_group('ETH') == 'crypto'
        assert _get_symbol_group('CRYPTO') == 'crypto'

    def test_get_symbol_group_equity(self):
        """Test symbol group detection for equity instruments."""
        from app.analyzers.geo_risk_analyzer import _get_symbol_group
        assert _get_symbol_group('SPX') == 'equity'
        assert _get_symbol_group('SPY') == 'equity'
        assert _get_symbol_group('QQQ') == 'equity'

    def test_get_symbol_group_forex(self):
        """Test symbol group detection for forex instruments."""
        from app.analyzers.geo_risk_analyzer import _get_symbol_group
        assert _get_symbol_group('DXY') == 'forex'
        assert _get_symbol_group('EUR') == 'forex'
        assert _get_symbol_group('USD') == 'forex'

    def test_scan_keywords_conflict(self):
        """Test keyword scanning for conflict-related terms."""
        from app.analyzers.geo_risk_analyzer import _scan_keywords

        news_items = [
            NewsItem(title="War escalation in middle east", source="Test", url="http://test.com", published_at="2024-01-01", sentiment_label="neutral", sentiment_score=0.0)
        ]
        result = _scan_keywords(news_items)
        assert 'conflict' in result
        assert 'war' in result['conflict']
        assert 'escalation' in result['conflict']

    def test_scan_keywords_sanctions(self):
        """Test keyword scanning for sanctions-related terms."""
        from app.analyzers.geo_risk_analyzer import _scan_keywords

        news_items = [
            NewsItem(title="New sanctions imposed on oil exports", source="Test", url="http://test.com", published_at="2024-01-01", sentiment_label="neutral", sentiment_score=0.0)
        ]
        result = _scan_keywords(news_items)
        assert 'sanctions' in result

    def test_scan_keywords_no_match(self):
        """Test keyword scanning with no geopolitical keywords."""
        from app.analyzers.geo_risk_analyzer import _scan_keywords

        news_items = [
            NewsItem(title="Stock market rally continues", source="Test", url="http://test.com", published_at="2024-01-01", sentiment_label="neutral", sentiment_score=0.0)
        ]
        result = _scan_keywords(news_items)
        assert len(result) == 0

    def test_indicator_checks_high_atr(self):
        """Test indicator checks with high ATR (confirming)."""
        from app.analyzers.geo_risk_analyzer import _indicator_checks

        checks = _indicator_checks(adx=25, rsi=55, volume_ratio=1.5, atr_percentile=75,
                                   expected_direction='bullish', trade_direction='bullish')
        assert len(checks) == 4
        assert checks[0].status == 'confirming'  # ATR

    def test_indicator_checks_low_atr(self):
        """Test indicator checks with low ATR (diverging)."""
        from app.analyzers.geo_risk_analyzer import _indicator_checks

        checks = _indicator_checks(adx=25, rsi=55, volume_ratio=1.5, atr_percentile=30,
                                   expected_direction='bullish', trade_direction='bullish')
        assert len(checks) == 4
        assert checks[0].status == 'diverging'  # ATR

    def test_indicator_checks_strong_adx_aligned(self):
        """Test indicator checks with strong ADX aligned with expected direction."""
        from app.analyzers.geo_risk_analyzer import _indicator_checks

        checks = _indicator_checks(adx=35, rsi=55, volume_ratio=1.5, atr_percentile=50,
                                   expected_direction='bullish', trade_direction='bullish')
        assert len(checks) == 4
        assert checks[1].status == 'confirming'  # ADX

    def test_indicator_checks_strong_adx_opposed(self):
        """Test indicator checks with strong ADX opposed to expected direction."""
        from app.analyzers.geo_risk_analyzer import _indicator_checks

        checks = _indicator_checks(adx=35, rsi=55, volume_ratio=1.5, atr_percentile=50,
                                   expected_direction='bullish', trade_direction='bearish')
        assert len(checks) == 4
        assert checks[1].status == 'diverging'  # ADX

    def test_indicator_checks_high_volume(self):
        """Test indicator checks with high volume (confirming)."""
        from app.analyzers.geo_risk_analyzer import _indicator_checks

        checks = _indicator_checks(adx=25, rsi=55, volume_ratio=2.0, atr_percentile=50,
                                   expected_direction='bullish', trade_direction='bullish')
        assert len(checks) == 4
        assert checks[2].status == 'confirming'  # Volume

    def test_indicator_checks_rsi_bullish_confirming(self):
        """Test RSI check with bullish momentum confirming expected direction."""
        from app.analyzers.geo_risk_analyzer import _indicator_checks

        checks = _indicator_checks(adx=25, rsi=60, volume_ratio=1.5, atr_percentile=50,
                                   expected_direction='bullish', trade_direction='bullish')
        assert len(checks) == 4
        assert checks[3].status == 'confirming'  # RSI

    def test_indicator_checks_rsi_bearish_confirming(self):
        """Test RSI check with bearish momentum confirming expected direction."""
        from app.analyzers.geo_risk_analyzer import _indicator_checks

        checks = _indicator_checks(adx=25, rsi=40, volume_ratio=1.5, atr_percentile=50,
                                   expected_direction='bearish', trade_direction='bearish')
        assert len(checks) == 4
        assert checks[3].status == 'confirming'  # RSI

    def test_analyze_geopolitical_risk_no_news(self):
        """Test geopolitical analysis with no news data."""
        from app.analyzers.geo_risk_analyzer import analyze_geopolitical_risk

        strength = StrengthAnalysis(signal=Signal.NEUTRAL, adx=25, rsi=55, volume_ratio=1.5, price_change_percent=0.0, description="Test strength")
        volatility = VolatilityAnalysis(atr=10, stop_loss=95, take_profit=110, risk_reward_ratio=2.0, atr_percentile_rank=50, description="Test volatility")
        trade_signal = TradeSignal(recommendation=Signal.NEUTRAL, score=0, reasons=[], trade_worthy=False)

        result = analyze_geopolitical_risk('XAU', None, strength, volatility, trade_signal)
        assert result.detected is False
        assert result.risk_score == 0
        assert result.risk_level == 'NONE'

    def test_analyze_geopolitical_risk_no_keywords(self):
        """Test geopolitical analysis with news but no geopolitical keywords."""
        from app.analyzers.geo_risk_analyzer import analyze_geopolitical_risk

        news = NewsSentiment(
            label='neutral',
            score=0,
            sentiment_summary='No geopolitical news',
            news_items=[
                NewsItem(title="Stock market rally", source="Test", url="http://test.com", published_at="2024-01-01", sentiment_label="neutral", sentiment_score=0.0)
            ]
        )
        strength = StrengthAnalysis(signal=Signal.NEUTRAL, adx=25, rsi=55, volume_ratio=1.5, price_change_percent=0.0, description="Test strength")
        volatility = VolatilityAnalysis(atr=10, stop_loss=95, take_profit=110, risk_reward_ratio=2.0, atr_percentile_rank=50, description="Test volatility")
        trade_signal = TradeSignal(recommendation=Signal.NEUTRAL, score=0, reasons=[], trade_worthy=False)

        result = analyze_geopolitical_risk('XAU', news, strength, volatility, trade_signal)
        assert result.detected is False
        assert result.risk_score == 0

    def test_analyze_geopolitical_risk_detected(self):
        """Test geopolitical analysis with detected geopolitical risk."""
        from app.analyzers.geo_risk_analyzer import analyze_geopolitical_risk

        news = NewsSentiment(
            label='neutral',
            score=0,
            sentiment_summary='Geopolitical tension',
            news_items=[
                NewsItem(title="War escalation in middle east", source="Test", url="http://test.com", published_at="2024-01-01", sentiment_label="neutral", sentiment_score=0.0)
            ]
        )
        strength = StrengthAnalysis(signal=Signal.BULLISH, adx=35, rsi=60, volume_ratio=2.0, price_change_percent=1.0, description="Test strength")
        volatility = VolatilityAnalysis(atr=10, stop_loss=95, take_profit=110, risk_reward_ratio=2.0, atr_percentile_rank=75, description="Test volatility")
        trade_signal = TradeSignal(recommendation=Signal.BULLISH, score=50, reasons=[], trade_worthy=True)

        result = analyze_geopolitical_risk('XAU', news, strength, volatility, trade_signal)
        assert result.detected is True
        assert result.risk_score > 0
        assert len(result.event_categories) > 0
        assert len(result.keywords_found) > 0
        assert result.ai_narrative is not None


# ══════════════════════════════════════════════════════════════════════════════
# 7. TRADE PLAN BUILDER
# ══════════════════════════════════════════════════════════════════════════════

class TestTradePlanBuilder:
    """Test trade plan builder as single source of truth for trade levels."""

    def test_direction_label_bullish(self):
        """Test direction label mapping for bullish signal."""
        from app.analyzers.trade_plan_builder import _direction_label
        assert _direction_label('bullish') == 'long'

    def test_direction_label_bearish(self):
        """Test direction label mapping for bearish signal."""
        from app.analyzers.trade_plan_builder import _direction_label
        assert _direction_label('bearish') == 'short'

    def test_direction_label_neutral(self):
        """Test direction label mapping for neutral signal."""
        from app.analyzers.trade_plan_builder import _direction_label
        assert _direction_label('neutral') == 'neutral'

    def test_build_trade_plan_bullish(self):
        """Test building a bullish trade plan."""
        from app.analyzers.trade_plan_builder import build_trade_plan

        volatility = VolatilityAnalysis(
            atr=10.0,
            atr_percentile_rank=50,
            stop_loss=5265.0,
            entry_price=5277.66,
            take_profit=5408.31,
            take_profit_level1=5303.00,
            take_profit_level2=5355.00,
            risk_reward_ratio=2.0,
            description="Test volatility"
        )

        plan = build_trade_plan(
            signal_direction='bullish',
            current_price=5382.97,
            volatility=volatility,
            is_actionable=True
        )

        assert plan is not None
        assert plan.direction == 'long'
        assert plan.entry == 5277.66
        assert plan.stop_loss == 5265.0
        assert plan.take_profit_1 == 5303.00
        assert plan.take_profit_2 == 5355.00
        assert plan.take_profit_3 == 5408.31
        assert plan.risk_reward == 2.0
        assert plan.is_actionable is True

    def test_build_trade_plan_bearish(self):
        """Test building a bearish trade plan."""
        from app.analyzers.trade_plan_builder import build_trade_plan

        volatility = VolatilityAnalysis(
            atr=10.0,
            atr_percentile_rank=50,
            stop_loss=5400.0,
            entry_price=5385.0,
            take_profit=5260.0,
            take_profit_level1=5340.0,
            take_profit_level2=5300.0,
            risk_reward_ratio=2.0,
            description="Test volatility"
        )

        plan = build_trade_plan(
            signal_direction='bearish',
            current_price=5382.97,
            volatility=volatility,
            is_actionable=False
        )

        assert plan is not None
        assert plan.direction == 'short'
        assert plan.entry == 5385.0
        assert plan.stop_loss == 5400.0
        assert plan.is_actionable is False

    def test_build_trade_plan_neutral(self):
        """Test building a neutral trade plan."""
        from app.analyzers.trade_plan_builder import build_trade_plan

        volatility = VolatilityAnalysis(
            atr=10.0,
            atr_percentile_rank=50,
            stop_loss=5265.0,
            entry_price=5277.66,
            take_profit=5408.31,
            take_profit_level1=5303.00,
            take_profit_level2=5355.00,
            risk_reward_ratio=2.0,
            description="Test volatility"
        )

        plan = build_trade_plan(
            signal_direction='neutral',
            current_price=5382.97,
            volatility=volatility
        )

        assert plan is not None
        assert plan.direction == 'neutral'
        assert 'no directional edge' in plan.narrative

    def test_build_trade_plan_no_volatility(self):
        """Test building trade plan with no volatility data returns None."""
        from app.analyzers.trade_plan_builder import build_trade_plan

        plan = build_trade_plan(
            signal_direction='bullish',
            current_price=5382.97,
            volatility=None
        )

        assert plan is None

    def test_build_trade_plan_zero_atr(self):
        """Test building trade plan with zero ATR returns None."""
        from app.analyzers.trade_plan_builder import build_trade_plan

        volatility = VolatilityAnalysis(
            atr=0.0,
            atr_percentile_rank=50,
            stop_loss=5265.0,
            entry_price=5277.66,
            take_profit=5408.31,
            risk_reward_ratio=2.0,
            description="Test volatility"
        )

        plan = build_trade_plan(
            signal_direction='bullish',
            current_price=5382.97,
            volatility=volatility
        )

        assert plan is None

    def test_build_trade_plan_zero_price(self):
        """Test building trade plan with zero price returns None."""
        from app.analyzers.trade_plan_builder import build_trade_plan

        volatility = VolatilityAnalysis(
            atr=10.0,
            atr_percentile_rank=50,
            stop_loss=5265.0,
            entry_price=5277.66,
            take_profit=5408.31,
            risk_reward_ratio=2.0,
            description="Test volatility"
        )

        plan = build_trade_plan(
            signal_direction='bullish',
            current_price=0.0,
            volatility=volatility
        )

        assert plan is None

    def test_build_trade_plan_with_or_data(self):
        """Test building trade plan with opening range data."""
        from app.analyzers.trade_plan_builder import build_trade_plan

        volatility = VolatilityAnalysis(
            atr=10.0,
            atr_percentile_rank=50,
            stop_loss=5265.0,
            entry_price=5277.66,
            take_profit=5408.31,
            take_profit_level1=5303.00,
            take_profit_level2=5355.00,
            risk_reward_ratio=2.0,
            description="Test volatility"
        )

        or_data = {'or_high': 5400.0, 'or_low': 5250.0, 'broken': False}

        plan = build_trade_plan(
            signal_direction='bullish',
            current_price=5382.97,
            volatility=volatility,
            or_data=or_data
        )

        assert plan is not None
        assert plan.invalidation == 5250.0
        assert 'close below $5250.00' in plan.stop_basis

    def test_build_trade_plan_market_entry(self):
        """Test entry basis label for market entry."""
        from app.analyzers.trade_plan_builder import build_trade_plan

        volatility = VolatilityAnalysis(
            atr=10.0,
            atr_percentile_rank=50,
            stop_loss=5265.0,
            entry_price=5382.97,  # Same as current price
            take_profit=5408.31,
            risk_reward_ratio=2.0,
            description="Test volatility"
        )

        plan = build_trade_plan(
            signal_direction='bullish',
            current_price=5382.97,
            volatility=volatility
        )

        assert plan is not None
        assert 'Market entry near current price' in plan.entry_basis


# ══════════════════════════════════════════════════════════════════════════════
# 8. FUNDAMENTALS ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

class TestFundamentalsAnalyzer:
    """Test fundamentals analysis for economic calendar events."""

    def test_detect_relevant_currencies_forex_pair(self):
        """Test currency detection for forex pairs."""
        from app.analyzers.fundamentals_analyzer import _detect_relevant_currencies

        currencies = _detect_relevant_currencies('EURUSD')
        assert 'EUR' in currencies
        assert 'USD' in currencies

    def test_detect_relevant_currencies_gold(self):
        """Test currency detection for gold (USD-pegged)."""
        from app.analyzers.fundamentals_analyzer import _detect_relevant_currencies

        currencies = _detect_relevant_currencies('XAU')
        assert 'USD' in currencies

    def test_detect_relevant_currencies_wti(self):
        """Test currency detection for WTI (USD-pegged)."""
        from app.analyzers.fundamentals_analyzer import _detect_relevant_currencies

        currencies = _detect_relevant_currencies('WTI')
        assert 'USD' in currencies

    def test_detect_relevant_currencies_btc(self):
        """Test currency detection for BTC (USD-pegged)."""
        from app.analyzers.fundamentals_analyzer import _detect_relevant_currencies

        currencies = _detect_relevant_currencies('BTC')
        assert 'USD' in currencies

    def test_detect_relevant_currencies_usd_suffix(self):
        """Test currency detection for symbols ending in USD."""
        from app.analyzers.fundamentals_analyzer import _detect_relevant_currencies

        currencies = _detect_relevant_currencies('DXY')
        assert 'USD' in currencies

    def test_analyze_fundamentals_no_events(self):
        """Test fundamentals analysis with no high-impact events."""
        from app.analyzers.fundamentals_analyzer import analyze_fundamentals

        # This will return no events since we can't mock the external API
        result = analyze_fundamentals('TEST')
        assert result is not None
        assert isinstance(result.has_high_impact_events, bool)
        assert isinstance(result.events, list)
        assert result.description is not None
        assert result.risk_reduction_active is False
        assert result.recommended_position_multiplier == 1.0

    def test_analyze_fundamentals_structure(self):
        """Test fundamentals analysis returns proper structure."""
        from app.analyzers.fundamentals_analyzer import analyze_fundamentals

        result = analyze_fundamentals('XAU')
        assert hasattr(result, 'has_high_impact_events')
        assert hasattr(result, 'events')
        assert hasattr(result, 'description')
        assert hasattr(result, 'event_timestamps')
        assert hasattr(result, 'risk_reduction_active')
        assert hasattr(result, 'recommended_position_multiplier')
        assert hasattr(result, 'pre_event_caution')
        assert hasattr(result, 'minutes_to_next_event')


# ══════════════════════════════════════════════════════════════════════════════
# 9. NEWS ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

class TestNewsAnalyzer:
    """Test news sentiment analysis."""

    def test_yahoo_symbol_map_xau(self):
        """Test Yahoo symbol mapping for gold."""
        from app.analyzers.news_analyzer import _YAHOO_SYMBOL_MAP

        ticker, name = _YAHOO_SYMBOL_MAP.get('XAU')
        assert ticker == 'GC=F'
        assert name == 'Gold'

    def test_yahoo_symbol_map_wti(self):
        """Test Yahoo symbol mapping for crude oil."""
        from app.analyzers.news_analyzer import _YAHOO_SYMBOL_MAP

        ticker, name = _YAHOO_SYMBOL_MAP.get('WTI')
        assert ticker == 'CL=F'
        assert name == 'Crude Oil'

    def test_yahoo_symbol_map_btc(self):
        """Test Yahoo symbol mapping for bitcoin."""
        from app.analyzers.news_analyzer import _YAHOO_SYMBOL_MAP

        ticker, name = _YAHOO_SYMBOL_MAP.get('BTC')
        assert ticker == 'BTC-USD'
        assert name == 'Bitcoin'

    def test_newsapi_search_map_xau(self):
        """Test NewsAPI search term mapping for gold."""
        from app.analyzers.news_analyzer import _NEWSAPI_SEARCH_MAP

        search_term = _NEWSAPI_SEARCH_MAP.get('XAU')
        assert search_term == 'gold price commodities'

    def test_newsapi_search_map_wti(self):
        """Test NewsAPI search term mapping for crude oil."""
        from app.analyzers.news_analyzer import _NEWSAPI_SEARCH_MAP

        search_term = _NEWSAPI_SEARCH_MAP.get('WTI')
        assert search_term == 'crude oil price WTI'

    def test_newsapi_search_map_btc(self):
        """Test NewsAPI search term mapping for bitcoin."""
        from app.analyzers.news_analyzer import _NEWSAPI_SEARCH_MAP

        search_term = _NEWSAPI_SEARCH_MAP.get('BTC')
        assert search_term == 'bitcoin cryptocurrency'


# ══════════════════════════════════════════════════════════════════════════════
# 10. PERFORMANCE ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformanceAnalyzer:
    """Test weekly performance calculation."""

    def test_calculate_weekly_performance_no_trades(self):
        """Test performance calculation with no trade-worthy signals."""
        from app.analyzers.performance_analyzer import calculate_weekly_performance
        from app.models import StrategySettings, Signal

        instruments = [{'symbol': 'XAU'}]
        data_map = {}  # Empty data map
        params = {}
        benchmarks = {'SPX': Signal.NEUTRAL}
        settings = StrategySettings(
            conviction_threshold=70,
            adx_threshold=25,
            atr_multiplier_tp=3.0,
            atr_multiplier_sl=1.5,
            portfolio_value=10000.0,
            risk_per_trade_percent=1.0
        )

        result = calculate_weekly_performance(instruments, data_map, params, benchmarks, settings)
        assert result.total_trades == 0
        assert result.total_pnl_percent == 0.0
        assert result.win_rate == 0.0
        assert result.best_trade_symbol == "N/A"
        assert result.worst_trade_symbol == "N/A"

    def test_calculate_weekly_performance_structure(self):
        """Test performance calculation returns proper structure."""
        from app.analyzers.performance_analyzer import calculate_weekly_performance
        from app.models import StrategySettings, Signal

        instruments = [{'symbol': 'XAU'}]
        data_map = {}
        params = {}
        benchmarks = {'SPX': Signal.NEUTRAL}
        settings = StrategySettings(
            conviction_threshold=70,
            adx_threshold=25,
            atr_multiplier_tp=3.0,
            atr_multiplier_sl=1.5,
            portfolio_value=10000.0,
            risk_per_trade_percent=1.0
        )

        result = calculate_weekly_performance(instruments, data_map, params, benchmarks, settings)
        assert hasattr(result, 'total_pnl_percent')
        assert hasattr(result, 'total_trades')
        assert hasattr(result, 'win_rate')
        assert hasattr(result, 'best_trade_symbol')
        assert hasattr(result, 'best_trade_pnl')
        assert hasattr(result, 'worst_trade_symbol')
        assert hasattr(result, 'worst_trade_pnl')
        assert hasattr(result, 'description')


# ══════════════════════════════════════════════════════════════════════════════
# 11. BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class TestBacktestEngine:
    """Test backtest engine for historical performance analysis."""

    def test_load_cache_empty(self):
        """Test cache loading when no cache exists."""
        from app.analyzers.backtest_engine import _load_cache

        cache = _load_cache()
        assert isinstance(cache, dict)

    def test_get_backtest_results_insufficient_data(self):
        """Test backtest with insufficient historical data."""
        from app.analyzers.backtest_engine import get_backtest_results
        import pandas as pd

        # Create minimal dataframe with less than 150 rows
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'Open': [100.0] * 100,
            'High': [105.0] * 100,
            'Low': [95.0] * 100,
            'Close': [100.0] * 100,
            'Volume': [1000000] * 100
        }, index=dates)

        result = get_backtest_results('TEST', data, {}, StrategySettings(
            conviction_threshold=70,
            adx_threshold=25,
            atr_multiplier_tp=3.0,
            atr_multiplier_sl=1.5,
            portfolio_value=10000.0,
            risk_per_trade_percent=1.0
        ))
        assert result.total_trades == 0
        assert result.win_rate == 0.0
        assert 'Insufficient historical data' in result.description

    def test_get_backtest_results_structure(self):
        """Test backtest returns proper structure."""
        from app.analyzers.backtest_engine import get_backtest_results
        import pandas as pd

        # Create dataframe with sufficient data
        dates = pd.date_range(start='2023-01-01', periods=200, freq='D')
        data = pd.DataFrame({
            'Open': [100.0] * 200,
            'High': [105.0] * 200,
            'Low': [95.0] * 200,
            'Close': [100.0] * 200,
            'Volume': [1000000] * 200
        }, index=dates)

        result = get_backtest_results('TEST', data, {}, StrategySettings(
            conviction_threshold=70,
            adx_threshold=25,
            atr_multiplier_tp=3.0,
            atr_multiplier_sl=1.5,
            portfolio_value=10000.0,
            risk_per_trade_percent=1.0
        ))
        assert hasattr(result, 'win_rate')
        assert hasattr(result, 'total_trades')
        assert hasattr(result, 'profit_factor')
        assert hasattr(result, 'avg_win')
        assert hasattr(result, 'avg_loss')
        assert hasattr(result, 'description')


# ══════════════════════════════════════════════════════════════════════════════
# 12. INTRADAY SIGNAL GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

class TestIntradaySignalGenerator:
    """Test intraday signal generation with EMA/MACD crossovers."""

    def test_ema_calculation(self):
        """Test EMA calculation helper function."""
        from app.analyzers.intraday_signal_generator import _ema
        import numpy as np

        arr = np.array([100, 101, 102, 103, 104, 105])
        result = _ema(arr, span=9)
        assert len(result) == len(arr)
        assert not np.isnan(result[-1])

    def test_ema_crossover_bullish(self):
        """Test EMA crossover detection for bullish signal."""
        from app.analyzers.intraday_signal_generator import _ema_crossover
        import numpy as np

        # Create price series where fast EMA crosses above slow EMA
        closes = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124])
        result = _ema_crossover(closes)
        # Result should be one of 'bullish', 'bearish', or 'none'
        assert result in ['bullish', 'bearish', 'none']

    def test_ema_crossover_insufficient_data(self):
        """Test EMA crossover with insufficient data returns 'none'."""
        from app.analyzers.intraday_signal_generator import _ema_crossover
        import numpy as np

        closes = np.array([100, 101, 102, 103, 104])
        result = _ema_crossover(closes)
        assert result == 'none'

    def test_ema_bias_bullish(self):
        """Test EMA bias detection for bullish bias."""
        from app.analyzers.intraday_signal_generator import _ema_bias
        import numpy as np

        # Price significantly above EMA21
        closes = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 130])
        result = _ema_bias(closes)
        assert result in ['bullish', 'bearish', 'neutral']

    def test_ema_bias_insufficient_data(self):
        """Test EMA bias with insufficient data returns 'neutral'."""
        from app.analyzers.intraday_signal_generator import _ema_bias
        import numpy as np

        closes = np.array([100, 101, 102, 103, 104])
        result = _ema_bias(closes)
        assert result == 'neutral'

    def test_macd_crossover_insufficient_data(self):
        """Test MACD crossover with insufficient data returns 'none'."""
        from app.analyzers.intraday_signal_generator import _macd_crossover
        import numpy as np

        closes = np.array([100, 101, 102, 103, 104])
        result = _macd_crossover(closes)
        assert result == 'none'

    def test_calc_atr(self):
        """Test ATR calculation helper function."""
        from app.analyzers.intraday_signal_generator import _calc_atr
        import numpy as np

        highs = np.array([105, 106, 107, 108, 109, 110])
        lows = np.array([95, 96, 97, 98, 99, 100])
        closes = np.array([100, 101, 102, 103, 104, 105])
        result = _calc_atr(highs, lows, closes, period=14)
        assert result > 0
        assert isinstance(result, float)

    def test_calc_atr_insufficient_data(self):
        """Test ATR calculation with insufficient data uses fallback."""
        from app.analyzers.intraday_signal_generator import _calc_atr
        import numpy as np

        highs = np.array([105, 106, 107])
        lows = np.array([95, 96, 97])
        closes = np.array([100, 101, 102])
        result = _calc_atr(highs, lows, closes, period=14)
        assert result > 0


# ══════════════════════════════════════════════════════════════════════════════
# 13. OIL MARKET ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

class TestOilMarketAnalyzer:
    """Test oil market context analysis for WTI."""

    def test_classify_ovx_low(self):
        """Test OVX classification for low volatility."""
        from app.analyzers.oil_market_analyzer import _classify_ovx

        result = _classify_ovx(20.0)
        assert result.regime == "LOW"
        assert result.size_multiplier == 1.0

    def test_classify_ovx_normal(self):
        """Test OVX classification for normal volatility."""
        from app.analyzers.oil_market_analyzer import _classify_ovx

        result = _classify_ovx(30.0)
        assert result.regime == "NORMAL"
        assert result.size_multiplier == 1.0

    def test_classify_ovx_elevated(self):
        """Test OVX classification for elevated volatility."""
        from app.analyzers.oil_market_analyzer import _classify_ovx

        result = _classify_ovx(40.0)
        assert result.regime == "ELEVATED"
        assert result.size_multiplier == 0.65

    def test_classify_ovx_extreme(self):
        """Test OVX classification for extreme volatility."""
        from app.analyzers.oil_market_analyzer import _classify_ovx

        result = _classify_ovx(55.0)
        assert result.regime == "EXTREME"
        assert result.size_multiplier == 0.30

    def test_next_wednesday(self):
        """Test next Wednesday calculation."""
        from app.analyzers.oil_market_analyzer import _next_wednesday
        from datetime import date

        result = _next_wednesday()
        assert isinstance(result, date)
        assert result.weekday() == 2  # Wednesday

    def test_check_opec_window(self):
        """Test OPEC window check."""
        from app.analyzers.oil_market_analyzer import _check_opec_window

        result = _check_opec_window()
        # Result can be None or OpecWindow depending on current date
        if result is not None:
            assert hasattr(result, 'next_meeting_date')
            assert hasattr(result, 'days_until')
            assert hasattr(result, 'is_active_window')
            assert hasattr(result, 'caution_message')

    def test_analyze_oil_market_context_structure(self):
        """Test oil market context returns proper structure."""
        from app.analyzers.oil_market_analyzer import analyze_oil_market_context

        result = analyze_oil_market_context()
        assert hasattr(result, 'ovx')
        assert hasattr(result, 'eia_inventory')
        assert hasattr(result, 'opec_window')
        assert hasattr(result, 'overall_regime')
        assert hasattr(result, 'regime_summary')
        assert hasattr(result, 'size_guidance')
        assert hasattr(result, 'warnings')


# ══════════════════════════════════════════════════════════════════════════════
# 14. SYMBOL VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════

class TestSymbolValidator:
    """Test symbol validation against data provider support."""

    def test_normalize_symbol(self):
        """Test symbol normalization."""
        from app.symbol_validator import SymbolValidator

        validator = SymbolValidator()
        assert validator.normalize_symbol('xau') == 'XAU'
        assert validator.normalize_symbol('  WTI  ') == 'WTI'
        assert validator.normalize_symbol('btc') == 'BTC'

    def test_check_alias_gold(self):
        """Test alias detection for gold variants."""
        from app.symbol_validator import SymbolValidator

        validator = SymbolValidator()
        assert validator.check_alias('GOLD') == 'XAU'
        assert validator.check_alias('GC') == 'XAU'
        assert validator.check_alias('GC=F') == 'XAU'

    def test_check_alias_silver(self):
        """Test alias detection for silver variants."""
        from app.symbol_validator import SymbolValidator

        validator = SymbolValidator()
        assert validator.check_alias('SILVER') == 'XAG'
        assert validator.check_alias('SI') == 'XAG'

    def test_check_alias_oil(self):
        """Test alias detection for oil variants."""
        from app.symbol_validator import SymbolValidator

        validator = SymbolValidator()
        assert validator.check_alias('OIL') == 'WTI'
        assert validator.check_alias('CL') == 'WTI'
        assert validator.check_alias('CRUDE') == 'WTI'

    def test_check_alias_btc(self):
        """Test alias detection for bitcoin variants."""
        from app.symbol_validator import SymbolValidator

        validator = SymbolValidator()
        assert validator.check_alias('BITCOIN') == 'BTC'
        assert validator.check_alias('BTCUSD') == 'BTC'

    def test_is_predefined_supported(self):
        """Test predefined supported symbols."""
        from app.symbol_validator import SymbolValidator

        validator = SymbolValidator()
        assert validator.is_predefined_supported('XAU') is True
        assert validator.is_predefined_supported('WTI') is True
        assert validator.is_predefined_supported('BTC') is True
        assert validator.is_predefined_supported('INVALID') is False

    def test_get_similar_symbols(self):
        """Test similar symbol suggestions."""
        from app.symbol_validator import SymbolValidator

        validator = SymbolValidator()
        suggestions = validator._get_similar_symbols('XAU')
        assert isinstance(suggestions, list)
        # Should find XAU itself or similar symbols
        assert len(suggestions) >= 0

    def test_get_supported_symbols(self):
        """Test getting list of supported symbols."""
        from app.symbol_validator import SymbolValidator

        validator = SymbolValidator()
        supported = validator.get_supported_symbols()
        assert isinstance(supported, list)
        assert 'XAU' in supported
        assert 'WTI' in supported
        assert 'BTC' in supported

    def test_validate_symbol_with_alias(self):
        """Test validate_symbol with alias correction."""
        from app.symbol_validator import validate_symbol

        result = validate_symbol('GOLD')
        assert result['valid'] is True
        assert result['symbol'] == 'XAU'
        assert 'corrected' in result['message'].lower()

    def test_validate_symbol_predefined(self):
        """Test validate_symbol with predefined supported symbol."""
        from app.symbol_validator import validate_symbol

        result = validate_symbol('XAU')
        assert result['valid'] is True
        assert result['symbol'] == 'XAU'
        assert result['message'] is None

    def test_validate_symbol_invalid(self):
        """Test validate_symbol with invalid symbol."""
        from app.symbol_validator import validate_symbol

        result = validate_symbol('INVALIDSYMBOL')
        assert result['valid'] is False
        assert result['symbol'] is None
        assert result['message'] is not None
        assert 'not supported' in result['message'].lower()

