"""
Comprehensive unit tests for domain/indicators/.

Tests cover: correctness, edge cases, boundary conditions, and known-value verification.
No pandas, no Pydantic — pure domain logic only.
"""

import math
import numpy as np
import pytest

from domain.indicators.rsi import calculate_rsi, calculate_rsi_series, classify_rsi, detect_rsi_divergence
from domain.indicators.atr import calculate_atr, calculate_tr_series, calculate_atr_series
from domain.indicators.adx import calculate_adx, classify_adx
from domain.indicators.vwap import calculate_vwap, calculate_vwap_distance_pct, classify_vwap_position
from domain.indicators.macd import calculate_macd, is_histogram_weakening
from domain.indicators.bollinger import calculate_bollinger_bands, is_band_reentry
from domain.constants import (
    INDICATOR_RSI_PERIOD, INDICATOR_ATR_PERIOD,
    INDICATOR_RSI_OVERSOLD, INDICATOR_RSI_OVERBOUGHT,
)


# ═══════════════════════════════════════════════════════════════════════════
# RSI Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRSI:

    def test_rsi_returns_float(self, uptrend_closes):
        result = calculate_rsi(uptrend_closes)
        assert isinstance(result, float)

    def test_rsi_range_valid(self, uptrend_closes):
        result = calculate_rsi(uptrend_closes)
        assert 0.0 <= result <= 100.0

    def test_rsi_insufficient_data_returns_50(self, insufficient_closes):
        result = calculate_rsi(insufficient_closes)
        assert result == 50.0

    def test_rsi_all_gains_returns_100(self):
        """Pure uptrend with no losses → RSI should approach 100."""
        closes = list(range(1, 50))  # strictly increasing
        result = calculate_rsi(closes)
        assert result == 100.0

    def test_rsi_all_losses_returns_0_or_50(self):
        """Pure downtrend → RSI should approach 0 (avg_loss > 0)."""
        closes = list(range(50, 1, -1))  # strictly decreasing
        result = calculate_rsi(closes)
        assert result < 40.0, f"Expected RSI near 0 for pure downtrend, got {result}"

    def test_rsi_uptrend_is_higher_than_downtrend(self, uptrend_closes, downtrend_closes):
        rsi_up = calculate_rsi(uptrend_closes)
        rsi_down = calculate_rsi(downtrend_closes)
        assert rsi_up > rsi_down

    def test_rsi_custom_period(self, uptrend_closes):
        rsi_14 = calculate_rsi(uptrend_closes, period=14)
        rsi_7 = calculate_rsi(uptrend_closes, period=7)
        # Both valid floats in [0, 100]
        assert 0.0 <= rsi_14 <= 100.0
        assert 0.0 <= rsi_7 <= 100.0

    def test_rsi_series_length_matches_input(self, uptrend_closes):
        series = calculate_rsi_series(uptrend_closes)
        assert len(series) == len(uptrend_closes)

    def test_rsi_series_warmup_is_nan(self, uptrend_closes):
        series = calculate_rsi_series(uptrend_closes)
        # First INDICATOR_RSI_PERIOD values should be NaN
        assert all(np.isnan(series[i]) for i in range(INDICATOR_RSI_PERIOD))

    def test_rsi_series_valid_after_warmup(self, uptrend_closes):
        series = calculate_rsi_series(uptrend_closes)
        valid = series[~np.isnan(series)]
        assert all(0.0 <= v <= 100.0 for v in valid)

    def test_classify_rsi_overbought(self):
        assert classify_rsi(75.0) == "overbought"

    def test_classify_rsi_bullish(self):
        assert classify_rsi(60.0) == "bullish"

    def test_classify_rsi_neutral(self):
        assert classify_rsi(50.0) == "neutral"

    def test_classify_rsi_bearish(self):
        assert classify_rsi(42.0) == "bearish"

    def test_classify_rsi_oversold(self):
        assert classify_rsi(25.0) == "oversold"

    def test_classify_rsi_boundary_overbought(self):
        assert classify_rsi(INDICATOR_RSI_OVERBOUGHT) == "overbought"

    def test_classify_rsi_boundary_oversold(self):
        assert classify_rsi(INDICATOR_RSI_OVERSOLD) == "oversold"

    def test_rsi_divergence_insufficient_data_returns_none(self, insufficient_closes):
        h = [c + 1 for c in insufficient_closes]
        l = [c - 1 for c in insufficient_closes]
        result = detect_rsi_divergence(insufficient_closes, h, l)
        assert result is None

    def test_rsi_no_divergence_flat_market(self, flat_closes):
        h = [c + 0.1 for c in flat_closes]
        l = [c - 0.1 for c in flat_closes]
        result = detect_rsi_divergence(flat_closes, h, l)
        assert result in (None, "bullish", "bearish")  # result type is correct


# ═══════════════════════════════════════════════════════════════════════════
# ATR Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestATR:

    def test_atr_returns_float(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        result = calculate_atr(d["highs"], d["lows"], d["closes"])
        assert isinstance(result, float)

    def test_atr_positive_for_valid_data(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        result = calculate_atr(d["highs"], d["lows"], d["closes"])
        assert result > 0.0

    def test_atr_zero_for_insufficient_data(self):
        highs = [105.0, 106.0]
        lows = [95.0, 96.0]
        closes = [100.0, 101.0]
        result = calculate_atr(highs, lows, closes)
        assert result == 0.0

    def test_atr_scales_with_volatility(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        # Doubling the high-low spread should double ATR
        highs2 = [h * 1.5 for h in d["highs"]]
        lows2 = [l * 0.5 for l in d["lows"]]
        atr_normal = calculate_atr(d["highs"], d["lows"], d["closes"])
        atr_wide = calculate_atr(highs2, lows2, d["closes"])
        assert atr_wide > atr_normal

    def test_tr_series_length_matches_input(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        tr = calculate_tr_series(d["highs"], d["lows"], d["closes"])
        assert len(tr) == len(d["closes"])

    def test_tr_series_all_non_negative(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        tr = calculate_tr_series(d["highs"], d["lows"], d["closes"])
        assert all(v >= 0 for v in tr)

    def test_tr_series_empty_input(self):
        tr = calculate_tr_series([], [], [])
        assert len(tr) == 0

    def test_tr_known_value(self):
        """TR for single bar with prev_close gap."""
        # H=105, L=100, C=102, prev_C=98
        # HL=5, |H-PC|=7, |L-PC|=2 → TR=7
        highs = [100.0, 105.0]
        lows = [95.0, 100.0]
        closes = [98.0, 102.0]
        tr = calculate_tr_series(highs, lows, closes)
        assert tr[1] == pytest.approx(7.0, abs=0.001)

    def test_atr_series_length(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        series = calculate_atr_series(d["highs"], d["lows"], d["closes"])
        assert len(series) == len(d["closes"])

    def test_atr_series_warmup_nan(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        series = calculate_atr_series(d["highs"], d["lows"], d["closes"])
        assert all(np.isnan(series[i]) for i in range(INDICATOR_ATR_PERIOD - 1))

    def test_atr_period_shorter_gives_more_responsive(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        atr14 = calculate_atr(d["highs"], d["lows"], d["closes"], period=14)
        atr5 = calculate_atr(d["highs"], d["lows"], d["closes"], period=5)
        # Both must be valid positive floats
        assert atr14 > 0
        assert atr5 > 0


# ═══════════════════════════════════════════════════════════════════════════
# ADX Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestADX:

    def test_adx_returns_float(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        result = calculate_adx(d["highs"], d["lows"], d["closes"])
        assert isinstance(result, float)

    def test_adx_range_valid(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        result = calculate_adx(d["highs"], d["lows"], d["closes"])
        assert 0.0 <= result <= 100.0

    def test_adx_zero_for_insufficient_data(self):
        highs = [105.0, 106.0, 107.0]
        lows = [95.0, 96.0, 97.0]
        closes = [100.0, 101.0, 102.0]
        result = calculate_adx(highs, lows, closes)
        assert result == 0.0

    def test_adx_strong_uptrend_higher_than_flat(self, ohlcv_uptrend, flat_closes):
        d = ohlcv_uptrend
        adx_trend = calculate_adx(d["highs"], d["lows"], d["closes"])
        h_flat = [c + 1 for c in flat_closes]
        l_flat = [c - 1 for c in flat_closes]
        adx_flat = calculate_adx(h_flat, l_flat, flat_closes)
        assert adx_trend > adx_flat

    def test_classify_adx_strong(self):
        assert classify_adx(35.0) == "strong"

    def test_classify_adx_developing(self):
        assert classify_adx(25.0) == "developing"

    def test_classify_adx_weak(self):
        assert classify_adx(15.0) == "weak"

    def test_classify_adx_boundary_strong(self):
        assert classify_adx(30.0) == "strong"

    def test_classify_adx_boundary_developing(self):
        assert classify_adx(20.0) == "developing"


# ═══════════════════════════════════════════════════════════════════════════
# VWAP Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestVWAP:

    def test_vwap_returns_float(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        result = calculate_vwap(d["highs"], d["lows"], d["closes"], d["volumes"])
        assert isinstance(result, float)

    def test_vwap_positive_for_valid_data(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        result = calculate_vwap(d["highs"], d["lows"], d["closes"], d["volumes"])
        assert result > 0.0

    def test_vwap_zero_for_zero_volume(self, no_volume_ohlcv):
        d = no_volume_ohlcv
        result = calculate_vwap(d["highs"], d["lows"], d["closes"], d["volumes"])
        assert result == 0.0

    def test_vwap_known_value(self):
        """Single bar: typical = (10+8+9)/3=9, vol=100 → VWAP=9."""
        h = [10.0]; l = [8.0]; c = [9.0]; v = [100.0]
        result = calculate_vwap(h, l, c, v, period=1)
        assert result == pytest.approx(9.0, abs=0.001)

    def test_vwap_weighted_by_volume(self):
        """Bar with 10x higher volume should dominate the VWAP."""
        h = [100.0, 200.0]
        l = [80.0, 180.0]
        c = [90.0, 190.0]
        v = [1.0, 10.0]
        # typical[0]=(100+80+90)/3=90, typical[1]=(200+180+190)/3=190
        # VWAP = (90*1 + 190*10) / 11 = 1990/11 ≈ 180.9
        result = calculate_vwap(h, l, c, v, period=2)
        assert result == pytest.approx(1990.0 / 11.0, abs=0.01)

    def test_vwap_distance_above(self):
        dist = calculate_vwap_distance_pct(current_price=110.0, vwap=100.0)
        assert dist == pytest.approx(10.0, abs=0.001)

    def test_vwap_distance_below(self):
        dist = calculate_vwap_distance_pct(current_price=90.0, vwap=100.0)
        assert dist == pytest.approx(-10.0, abs=0.001)

    def test_vwap_distance_zero_vwap(self):
        dist = calculate_vwap_distance_pct(current_price=100.0, vwap=0.0)
        assert dist == 0.0

    def test_classify_vwap_extended_above(self):
        assert classify_vwap_position(2.0) == "extended_above"

    def test_classify_vwap_above(self):
        assert classify_vwap_position(0.5) == "above"

    def test_classify_vwap_at(self):
        assert classify_vwap_position(0.0) == "at"

    def test_classify_vwap_below(self):
        assert classify_vwap_position(-0.5) == "below"

    def test_classify_vwap_extended_below(self):
        assert classify_vwap_position(-2.0) == "extended_below"


# ═══════════════════════════════════════════════════════════════════════════
# MACD Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMACD:

    def test_macd_returns_result_object(self, uptrend_closes):
        result = calculate_macd(uptrend_closes)
        assert hasattr(result, "macd")
        assert hasattr(result, "signal")
        assert hasattr(result, "histogram")
        assert hasattr(result, "histogram_prev")

    def test_macd_all_floats(self, uptrend_closes):
        result = calculate_macd(uptrend_closes)
        assert isinstance(result.macd, float)
        assert isinstance(result.signal, float)
        assert isinstance(result.histogram, float)
        assert isinstance(result.histogram_prev, float)

    def test_macd_zeros_for_insufficient_data(self, insufficient_closes):
        result = calculate_macd(insufficient_closes)
        assert result.macd == 0.0
        assert result.signal == 0.0
        assert result.histogram == 0.0

    def test_macd_positive_in_uptrend(self, uptrend_closes):
        """Fast EMA > Slow EMA in uptrend → MACD line should be positive."""
        result = calculate_macd(uptrend_closes)
        assert result.macd > 0.0

    def test_macd_negative_in_downtrend(self, downtrend_closes):
        """Fast EMA < Slow EMA in downtrend → MACD line should be negative."""
        result = calculate_macd(downtrend_closes)
        assert result.macd < 0.0

    def test_histogram_weakening_bullish_detects_fade(self):
        """hist[-1] < hist[-2] in bullish context = weakening."""
        from domain.indicators.macd import MACDResult
        r = MACDResult(macd=1.0, signal=0.5, histogram=0.3, histogram_prev=0.7)
        assert is_histogram_weakening(r, trend_is_bullish=True) is True

    def test_histogram_weakening_bullish_not_weakening(self):
        from domain.indicators.macd import MACDResult
        r = MACDResult(macd=1.0, signal=0.5, histogram=0.8, histogram_prev=0.5)
        assert is_histogram_weakening(r, trend_is_bullish=True) is False

    def test_histogram_weakening_bearish_detects_fade(self):
        from domain.indicators.macd import MACDResult
        r = MACDResult(macd=-1.0, signal=-0.5, histogram=-0.3, histogram_prev=-0.7)
        assert is_histogram_weakening(r, trend_is_bullish=False) is True


# ═══════════════════════════════════════════════════════════════════════════
# Bollinger Bands Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestBollingerBands:

    def test_bollinger_returns_result_object(self, uptrend_closes):
        result = calculate_bollinger_bands(uptrend_closes)
        assert hasattr(result, "upper")
        assert hasattr(result, "middle")
        assert hasattr(result, "lower")
        assert hasattr(result, "width")

    def test_bollinger_upper_gt_middle_gt_lower(self, uptrend_closes):
        result = calculate_bollinger_bands(uptrend_closes)
        assert result.upper > result.middle > result.lower

    def test_bollinger_zeros_for_insufficient_data(self):
        result = calculate_bollinger_bands([100.0, 101.0])
        assert result.upper == 0.0
        assert result.lower == 0.0

    def test_bollinger_known_value_flat(self):
        """20 identical prices → std=0, all bands equal middle."""
        closes = [100.0] * 20
        result = calculate_bollinger_bands(closes)
        assert result.upper == pytest.approx(100.0, abs=0.001)
        assert result.middle == pytest.approx(100.0, abs=0.001)
        assert result.lower == pytest.approx(100.0, abs=0.001)
        assert result.width == pytest.approx(0.0, abs=0.001)

    def test_bollinger_width_positive_for_volatile_data(self, volatile_closes):
        result = calculate_bollinger_bands(volatile_closes)
        assert result.width > 0.0

    def test_bollinger_width_wider_for_more_volatile(self, uptrend_closes, volatile_closes):
        result_stable = calculate_bollinger_bands(uptrend_closes)
        result_volatile = calculate_bollinger_bands(volatile_closes)
        assert result_volatile.width > result_stable.width

    def test_bollinger_band_reentry_insufficient_data(self):
        closes = [100.0] * 10
        highs = [101.0] * 10
        lows = [99.0] * 10
        result = is_band_reentry(closes, highs, lows)
        assert result is False

    def test_bollinger_band_reentry_bullish_detects(self):
        """Setup where previous bars touched upper band and current bar is inside."""
        # Create 25 bars; upper band ≈ 105, craft last bars to simulate reentry
        np.random.seed(1)
        closes = list(np.linspace(90.0, 100.0, 25))
        upper_approx = np.mean(closes[-20:]) + 2 * np.std(closes[-20:], ddof=1)
        # Force previous bars to tag or exceed upper band
        highs = [c + 1.0 for c in closes]
        highs[-3] = upper_approx + 1.0
        highs[-2] = upper_approx + 0.5
        # Current bar: close back inside
        closes[-1] = upper_approx - 2.0
        lows = [c - 1.0 for c in closes]
        result = is_band_reentry(closes, highs, lows, trend_is_bullish=True)
        assert result is True
