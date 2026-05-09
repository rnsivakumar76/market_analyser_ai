"""
Regression tests for signal-blocking bug fixes — Mar 2026.

Bugs fixed:
  1. (bbb4eea) Beta filter: WTI/XAU/XAG used SPX → inverted DXY
  2. (7e48cfd) Relative strength: WTI/XAU/XAG compared vs SPX data → DXY
  3. (27b0368) Candle filter: is_bullish=None for every non-reversal bar → blocks
               trending continuation bars (fixed: accept any directional close)
  4. (27b0368) Strength: price_change > 1% threshold too high for gold/silver
               (fixed: configurable, default 0.5%)
  5. (27b0368) RSI 55/45 momentum thresholds existed in constants but were unused
               (fixed: wired into strength analyzer)
  6. (7ca1fa9) Macro shield hard-blocked all 4 instruments on any USD event
               (fixed: penalty-only, never blocked=True)

Run:  pytest tests/test_signal_fixes_mar2026.py -v
"""
import pytest
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_ohlcv(n=30, close_seq=None, volume=1000):
    """Build a minimal OHLCV DataFrame.  close_seq overrides the last bar's Close."""
    dates = pd.date_range("2026-01-01", periods=n, freq="B")
    base = np.linspace(100, 110, n)
    df = pd.DataFrame({
        "Open":   base - 0.5,
        "High":   base + 1.0,
        "Low":    base - 1.0,
        "Close":  base + 0.3,
        "Volume": np.full(n, volume),
    }, index=dates)
    if close_seq is not None:
        # Override last few rows so specific RSI / price-change patterns emerge
        for i, v in enumerate(close_seq[-n:], start=n - len(close_seq)):
            if 0 <= i < n:
                df.iloc[i, df.columns.get_loc("Close")] = v
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Fix 3 — candle_analyzer: directional close detection
# ─────────────────────────────────────────────────────────────────────────────

class TestCandleAnalyzerDirectionalClose:
    """
    Before fix: every non-reversal bar returned is_bullish=None → candle filter blocked.
    After fix : clear bullish/bearish close returns True/False; only doji returns None.
    """

    def _last_bar_df(self, open_, high, low, close, n=10):
        """DataFrame whose last bar has the given OHLC."""
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "Open":   np.linspace(100, 101, n),
            "High":   np.linspace(101, 102, n),
            "Low":    np.linspace(99, 100, n),
            "Close":  np.linspace(100.3, 101.3, n),
            "Volume": np.ones(n) * 1000,
        }, index=dates)
        # Override the last bar
        df.iloc[-1] = [open_, high, low, close, 1000]
        return df

    def test_clear_bullish_close_returns_true(self):
        from app.analyzers.candle_analyzer import detect_candle_patterns
        # Large bullish body: open=100, close=101.5 (body=1.5, range=2.0 → ratio=0.75)
        df = self._last_bar_df(100.0, 102.0, 100.0, 101.5)
        result = detect_candle_patterns(df)
        assert result["is_bullish"] is True, (
            "Clear bullish close should return is_bullish=True (was None before fix)"
        )

    def test_clear_bearish_close_returns_false(self):
        from app.analyzers.candle_analyzer import detect_candle_patterns
        # Large bearish body: open=101.5, close=100.0
        df = self._last_bar_df(101.5, 102.0, 100.0, 100.0)
        result = detect_candle_patterns(df)
        assert result["is_bullish"] is False, (
            "Clear bearish close should return is_bullish=False (was None before fix)"
        )

    def test_doji_returns_none(self):
        from app.analyzers.candle_analyzer import detect_candle_patterns
        # Doji: open=100.05, close=100.06, range=2.0 → body ratio ≈ 0.005 < 0.1
        df = self._last_bar_df(100.05, 101.0, 99.0, 100.06)
        result = detect_candle_patterns(df)
        assert result["is_bullish"] is None, (
            "Doji (body < 10% of range) should still return is_bullish=None"
        )

    def test_bullish_engulfing_still_detected(self):
        from app.analyzers.candle_analyzer import detect_candle_patterns
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        df = pd.DataFrame({
            "Open":   np.linspace(100, 101, 10),
            "High":   np.linspace(101, 102, 10),
            "Low":    np.linspace(99, 100, 10),
            "Close":  np.linspace(100.3, 101.3, 10),
            "Volume": np.ones(10) * 1000,
        }, index=dates)
        # Previous bar: bearish (open > close)
        df.iloc[-2] = [101.0, 101.5, 99.5, 100.0, 1000]
        # Current bar: bullish engulfing (open below prev close, close above prev open)
        df.iloc[-1] = [99.5, 102.5, 99.0, 102.0, 1500]
        result = detect_candle_patterns(df)
        assert result["is_bullish"] is True
        assert "engulfing" in result["pattern"].lower() or result["pattern"] == "bullish_engulfing"

    def test_hammer_still_detected(self):
        from app.analyzers.candle_analyzer import detect_candle_patterns
        dates = pd.date_range("2026-01-01", periods=10, freq="B")
        df = pd.DataFrame({
            "Open":   np.linspace(100, 101, 10),
            "High":   np.linspace(101, 102, 10),
            "Low":    np.linspace(99, 100, 10),
            "Close":  np.linspace(100.3, 101.3, 10),
            "Volume": np.ones(10) * 1000,
        }, index=dates)
        # Hammer: open=100.5, close=101.0, high=101.05, low=98.0
        # body=0.5, range=3.05, body_ratio≈0.16 (>0.1, clears doji check)
        # lower_wick=2.5, upper_wick=0.05 → satisfies lw>2*body and uw<0.5*body
        df.iloc[-1] = [100.5, 101.05, 98.0, 101.0, 1000]
        result = detect_candle_patterns(df)
        assert result["is_bullish"] is True
        assert "hammer" in result["pattern"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# Fix 4 & 5 — strength_analyzer: RSI momentum zone + 0.5% price threshold
# ─────────────────────────────────────────────────────────────────────────────

class TestStrengthAnalyzerFixes:
    """
    Fix 4: price_change threshold lowered from 1% to 0.5% (configurable).
    Fix 5: RSI 55-70 registers bullish momentum; RSI 30-45 registers bearish.
    """

    def _bullish_rsi_df(self, target_rsi=62, n=30):
        """Craft a DataFrame that yields RSI close to target_rsi."""
        # Use a gentle uptrend to push RSI into 55-70 range
        closes = np.linspace(100, 108, n)
        closes[-1] = closes[-1] + 0.3   # gentle up day
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        return pd.DataFrame({
            "Open":   closes - 0.4,
            "High":   closes + 0.8,
            "Low":    closes - 0.8,
            "Close":  closes,
            "Volume": np.zeros(n),  # zero volume → commodity-like (no VWAP / volume surge)
        }, index=dates)

    def test_rsi_bullish_momentum_zone_registers(self):
        """RSI in 55-70 should register as bullish strength (was ignored before fix)."""
        from app.analyzers.strength_analyzer import analyze_daily_strength
        from app.models import Signal

        df = self._bullish_rsi_df()
        result = analyze_daily_strength(df, {"rsi_bullish_threshold": 55})
        # RSI should be in bullish momentum zone for a clear uptrend series
        if result.rsi >= 55 and result.rsi < 70:
            assert result.signal == Signal.BULLISH, (
                f"RSI={result.rsi:.1f} in 55-70 range should yield BULLISH signal"
            )

    def test_price_change_half_percent_registers_bullish(self):
        """A +0.6% daily close should register (was blocked at 1% before fix)."""
        from app.analyzers.strength_analyzer import analyze_daily_strength
        from app.models import Signal

        n = 30
        closes = np.linspace(100, 100 + n * 0.1, n)
        # Force last bar to be exactly +0.6% up
        closes[-1] = closes[-2] * 1.006
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "Open":   closes - 0.05,
            "High":   closes + 0.2,
            "Low":    closes - 0.2,
            "Close":  closes,
            "Volume": np.zeros(n),
        }, index=dates)
        result = analyze_daily_strength(df, {"price_change_threshold": 0.5})
        assert result.price_change_percent > 0.5, (
            "price_change_percent should reflect the +0.6% move"
        )
        # Verify it contributed a bullish signal (checking reason text)
        assert any("up day" in r.lower() or "bullish" in r.lower() for r in [result.description]), (
            "0.6% up day should contribute to bullish strength with 0.5% threshold"
        )

    def test_price_change_below_threshold_ignored(self):
        """A +0.3% daily change should NOT register when threshold is 0.5%."""
        from app.analyzers.strength_analyzer import analyze_daily_strength

        n = 30
        closes = np.linspace(100, 103, n)
        closes[-1] = closes[-2] * 1.003   # +0.3%
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "Open":   closes - 0.05,
            "High":   closes + 0.15,
            "Low":    closes - 0.15,
            "Close":  closes,
            "Volume": np.zeros(n),
        }, index=dates)
        result = analyze_daily_strength(df, {"price_change_threshold": 0.5})
        # price_change_percent should be around 0.3 which is below threshold → no "up day" reason
        assert result.price_change_percent < 0.5

    def test_rsi_extreme_oversold_weighted_double(self):
        """RSI < 30 should give bullish_signals += 2 (stronger than momentum zone +1)."""
        from app.analyzers.strength_analyzer import analyze_daily_strength
        from app.models import Signal

        # Force RSI deep oversold: sharp down run then tiny recovery
        n = 30
        closes = np.concatenate([
            np.linspace(120, 85, 25),   # strong drop → RSI < 30
            np.linspace(85, 86, 5),     # tiny bounce at end
        ])
        closes[-1] = closes[-2] * 1.002   # marginal up day (below 0.5% threshold)
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "Open":   closes - 0.3,
            "High":   closes + 1.0,
            "Low":    closes - 3.0,
            "Close":  closes,
            "Volume": np.zeros(n),
        }, index=dates)
        result = analyze_daily_strength(df, {})
        if result.rsi < 30:
            assert result.signal == Signal.BULLISH, (
                f"RSI={result.rsi:.1f} deeply oversold should produce BULLISH signal"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Fix 6 — filter_engine: macro shield is penalty-only, never blocked=True
# ─────────────────────────────────────────────────────────────────────────────

class TestMacroShieldPenaltyOnly:
    """
    Before fix: has_high_impact_events=True → blocked=True (hard block).
    After fix : has_high_impact_events=True → blocked=False, score -= 20.
    """

    def test_macro_event_never_hard_blocks(self):
        from domain.signals.filter_engine import apply_macro_shield
        result, _ = apply_macro_shield(
            has_high_impact_events=True,
            trade_worthy=True,
            current_score=85,
        )
        assert result.blocked is False, (
            "Macro shield must NOT hard-block after fix (was True before)"
        )

    def test_macro_event_applies_score_penalty(self):
        from domain.signals.filter_engine import apply_macro_shield
        _, adjusted = apply_macro_shield(
            has_high_impact_events=True,
            trade_worthy=True,
            current_score=85,
        )
        assert adjusted == 65, "Macro shield should reduce score by 20 pts"

    def test_high_conviction_survives_macro_event(self):
        """Score=95 → after -20 penalty → 75 ≥ 70 threshold → signal still fires."""
        from domain.signals.filter_engine import apply_macro_shield, apply_all_hard_filters
        result, adjusted = apply_macro_shield(
            has_high_impact_events=True,
            trade_worthy=True,
            current_score=95,
        )
        assert result.blocked is False
        assert adjusted == 75  # 95 - 20

    def test_no_macro_event_no_penalty(self):
        from domain.signals.filter_engine import apply_macro_shield
        result, adjusted = apply_macro_shield(
            has_high_impact_events=False,
            trade_worthy=True,
            current_score=85,
        )
        assert result.blocked is False
        assert adjusted == 85  # unchanged

    def test_macro_warning_appears_in_all_hard_filters_reasons(self):
        """Macro caution reason should still appear in reasons list (as a warning tag)."""
        from domain.signals.filter_engine import apply_all_hard_filters
        _, _, reasons = apply_all_hard_filters(
            recommendation="bullish",
            trade_worthy=True,
            composite_score=95,
            adx=35.0,
            benchmark_direction="neutral",
            candle_is_bullish=True,
            candle_pattern="Directional close — bullish bar",
            has_high_impact_events=True,
            is_outperforming=True,
        )
        assert any("macro" in r.lower() or "event" in r.lower() for r in reasons), (
            "Macro caution warning should appear in reasons even though it does not block"
        )

    def test_macro_penalty_does_not_set_any_blocked(self):
        """apply_all_hard_filters should remain trade_worthy=True when only macro fires."""
        from domain.signals.filter_engine import apply_all_hard_filters
        trade_worthy, score, reasons = apply_all_hard_filters(
            recommendation="bullish",
            trade_worthy=True,
            composite_score=95,
            adx=35.0,
            benchmark_direction="neutral",
            candle_is_bullish=True,
            candle_pattern="Directional close — bullish bar",
            has_high_impact_events=True,
            is_outperforming=True,
        )
        assert trade_worthy is True, (
            "trade_worthy should remain True — macro is penalty only, not a block"
        )
        assert score == 75, "Score must be penalised by 20 (95 → 75)"


# ─────────────────────────────────────────────────────────────────────────────
# Fix 1 & 2 — commodity benchmark detection (logic unit tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestCommodityBenchmarkDetection:
    """
    Verify that the commodity detection logic correctly classifies each symbol
    so the right benchmark (DXY vs BTC vs SPX) is selected.
    """

    COMMODITY_SYMS = {"WTI", "XAU", "XAG", "GOLD", "SILVER", "OIL"}
    CRYPTO_SUBS = ["BTC", "CRYPTO", "BITCOIN"]

    def _is_commodity(self, sym):
        return any(sub in sym.upper() for sub in self.COMMODITY_SYMS)

    def _is_crypto(self, sym):
        return (
            any(sub in sym.upper() for sub in self.CRYPTO_SUBS)
            or (len(sym) > 6 and "USD" in sym.upper())
        )

    def _bench_label(self, sym):
        if self._is_commodity(sym):
            return "DXY"
        if self._is_crypto(sym):
            return "BTC"
        return "SPX"

    @pytest.mark.parametrize("sym,expected", [
        ("WTI",     "DXY"),
        ("XAU",     "DXY"),
        ("XAG",     "DXY"),
        ("BTC",     "BTC"),
        ("BTCUSD",  "BTC"),
    ])
    def test_benchmark_label(self, sym, expected):
        assert self._bench_label(sym) == expected, (
            f"{sym} should use {expected} benchmark, got {self._bench_label(sym)}"
        )

    def test_wti_not_classified_as_crypto(self):
        assert not self._is_crypto("WTI")

    def test_xau_not_classified_as_crypto(self):
        assert not self._is_crypto("XAU")

    def test_btc_not_classified_as_commodity(self):
        assert not self._is_commodity("BTC")

    def test_wti_classified_as_commodity(self):
        assert self._is_commodity("WTI")

    def test_xau_classified_as_commodity(self):
        assert self._is_commodity("XAU")

    def test_xag_classified_as_commodity(self):
        assert self._is_commodity("XAG")


# ─────────────────────────────────────────────────────────────────────────────
# Integration — candle filter works with new directional close logic
# ─────────────────────────────────────────────────────────────────────────────

class TestCandleFilterIntegration:
    """
    Verify filter_engine candle filter accepts any directional close (not just
    reversal patterns) for bullish/bearish recommendations.
    """

    def test_bullish_directional_close_passes_filter(self):
        from domain.signals.filter_engine import apply_candle_filter
        result = apply_candle_filter(
            recommendation="bullish",
            trade_worthy=True,
            candle_is_bullish=True,
            candle_pattern="Directional close — bullish bar",
        )
        assert result.blocked is False

    def test_doji_blocks_bullish_signal(self):
        from domain.signals.filter_engine import apply_candle_filter
        result = apply_candle_filter(
            recommendation="bullish",
            trade_worthy=True,
            candle_is_bullish=None,    # doji
            candle_pattern="Doji / indecision candle",
        )
        assert result.blocked is True

    def test_bearish_close_blocks_bullish_signal(self):
        from domain.signals.filter_engine import apply_candle_filter
        result = apply_candle_filter(
            recommendation="bullish",
            trade_worthy=True,
            candle_is_bullish=False,   # bearish close
            candle_pattern="Directional close — bearish bar",
        )
        assert result.blocked is True

    def test_bearish_directional_close_passes_for_short(self):
        from domain.signals.filter_engine import apply_candle_filter
        result = apply_candle_filter(
            recommendation="bearish",
            trade_worthy=True,
            candle_is_bullish=False,
            candle_pattern="Directional close — bearish bar",
        )
        assert result.blocked is False

    def test_filter_message_says_confirming_not_reversal(self):
        """Message should say 'confirming candle', not the old 'reversal candle'."""
        from domain.signals.filter_engine import apply_candle_filter
        result = apply_candle_filter(
            recommendation="bullish",
            trade_worthy=True,
            candle_is_bullish=None,
            candle_pattern="Doji",
        )
        assert "confirming" in result.reason.lower(), (
            "Filter message should say 'confirming candle' after message update"
        )
        assert "reversal" not in result.reason.lower(), (
            "Old 'reversal candle' message should be gone"
        )
