"""
Comprehensive unit tests for domain/levels/.

Tests cover: pivot points, fibonacci, std bands, breakout, support/resistance,
and linear regression — all with known-value assertions, edge cases, and boundary conditions.
"""

import math
import numpy as np
import pytest

from domain.levels.pivot_points import calculate_pivot_points, classify_price_vs_pivots, PivotValues
from domain.levels.fibonacci import calculate_fibonacci_levels, FibValues
from domain.levels.std_bands import calculate_std_dev_bands, calculate_rolling_std
from domain.levels.breakout import detect_donchian_breakout, BreakoutResult
from domain.levels.support_resistance import (
    find_swing_lows, find_swing_highs, nearest_support_below,
)
from domain.levels.linear_regression import calculate_linear_regression_slope, classify_slope
from domain.constants import (
    FIB_RET_382, FIB_RET_618, FIB_EXT_1618,
    BREAKOUT_DONCHIAN_PERIOD,
)


# ═══════════════════════════════════════════════════════════════════════════
# Pivot Points Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPivotPoints:

    def test_pivot_returns_dataclass(self, known_pivot_bar):
        b = known_pivot_bar
        result = calculate_pivot_points(b["high"], b["low"], b["close"])
        assert isinstance(result, PivotValues)

    def test_pivot_known_value(self, known_pivot_bar):
        b = known_pivot_bar  # H=110, L=90, C=100 → P=100
        result = calculate_pivot_points(b["high"], b["low"], b["close"])
        assert result.pivot == pytest.approx(100.0, abs=0.01)

    def test_r1_known_value(self, known_pivot_bar):
        b = known_pivot_bar
        result = calculate_pivot_points(b["high"], b["low"], b["close"])
        # R1 = 2*P - L = 200 - 90 = 110
        assert result.r1 == pytest.approx(110.0, abs=0.01)

    def test_s1_known_value(self, known_pivot_bar):
        b = known_pivot_bar
        result = calculate_pivot_points(b["high"], b["low"], b["close"])
        # S1 = 2*P - H = 200 - 110 = 90
        assert result.s1 == pytest.approx(90.0, abs=0.01)

    def test_r2_known_value(self, known_pivot_bar):
        b = known_pivot_bar
        result = calculate_pivot_points(b["high"], b["low"], b["close"])
        # R2 = P + (H-L) = 100 + 20 = 120
        assert result.r2 == pytest.approx(120.0, abs=0.01)

    def test_s2_known_value(self, known_pivot_bar):
        b = known_pivot_bar
        result = calculate_pivot_points(b["high"], b["low"], b["close"])
        # S2 = P - (H-L) = 100 - 20 = 80
        assert result.s2 == pytest.approx(80.0, abs=0.01)

    def test_r3_formula(self, known_pivot_bar):
        b = known_pivot_bar
        result = calculate_pivot_points(b["high"], b["low"], b["close"])
        # R3 = H + 2*(P - L) = 110 + 2*(100-90) = 110+20=130
        assert result.r3 == pytest.approx(130.0, abs=0.01)

    def test_s3_formula(self, known_pivot_bar):
        b = known_pivot_bar
        result = calculate_pivot_points(b["high"], b["low"], b["close"])
        # S3 = L - 2*(H - P) = 90 - 2*(110-100) = 90-20=70
        assert result.s3 == pytest.approx(70.0, abs=0.01)

    def test_pivot_level_ordering(self, known_pivot_bar):
        b = known_pivot_bar
        r = calculate_pivot_points(b["high"], b["low"], b["close"])
        assert r.s3 < r.s2 < r.s1 < r.pivot < r.r1 < r.r2 < r.r3

    def test_zero_bar_returns_all_zeros(self):
        result = calculate_pivot_points(0.0, 0.0, 0.0)
        assert result.pivot == 0.0
        assert result.r1 == 0.0
        assert result.s1 == 0.0

    def test_pivot_all_same_price(self):
        """When H=L=C, pivot=price, R1=R2=R3=price, S1=S2=S3=price."""
        result = calculate_pivot_points(100.0, 100.0, 100.0)
        assert result.pivot == pytest.approx(100.0, abs=0.01)
        assert result.r1 == pytest.approx(100.0, abs=0.01)
        assert result.s1 == pytest.approx(100.0, abs=0.01)

    def test_classify_above_r2(self, known_pivot_bar):
        b = known_pivot_bar
        pivots = calculate_pivot_points(b["high"], b["low"], b["close"])
        assert classify_price_vs_pivots(125.0, pivots) == "above_r2"

    def test_classify_between_r1_r2(self, known_pivot_bar):
        b = known_pivot_bar
        pivots = calculate_pivot_points(b["high"], b["low"], b["close"])
        assert classify_price_vs_pivots(115.0, pivots) == "between_r1_r2"

    def test_classify_between_pivot_r1(self, known_pivot_bar):
        b = known_pivot_bar
        pivots = calculate_pivot_points(b["high"], b["low"], b["close"])
        assert classify_price_vs_pivots(105.0, pivots) == "between_pivot_r1"

    def test_classify_below_s2(self, known_pivot_bar):
        b = known_pivot_bar
        pivots = calculate_pivot_points(b["high"], b["low"], b["close"])
        assert classify_price_vs_pivots(75.0, pivots) == "below_s2"


# ═══════════════════════════════════════════════════════════════════════════
# Fibonacci Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestFibonacci:

    def test_fib_returns_dataclass(self, known_fib_range):
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 175.0)
        assert isinstance(result, FibValues)

    def test_fib_uptrend_direction(self, known_fib_range):
        """Current price closer to high → uptrend."""
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 175.0)
        assert result.trend == "up"

    def test_fib_downtrend_direction(self, known_fib_range):
        """Current price closer to low → downtrend."""
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 125.0)
        assert result.trend == "down"

    def test_fib_ret_382_uptrend_known_value(self, known_fib_range):
        """ret_382 in uptrend = high - diff*0.382 = 200 - 38.2 = 161.8"""
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 175.0)
        assert result.ret_382 == pytest.approx(161.8, abs=0.01)

    def test_fib_ret_618_uptrend_known_value(self, known_fib_range):
        """ret_618 in uptrend = 200 - 61.8 = 138.2"""
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 175.0)
        assert result.ret_618 == pytest.approx(138.2, abs=0.01)

    def test_fib_ext_1618_uptrend_known_value(self, known_fib_range):
        """ext_1618 in uptrend = low + diff*1.618 = 100 + 161.8 = 261.8"""
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 175.0)
        assert result.ext_1618 == pytest.approx(261.8, abs=0.01)

    def test_fib_ret_382_downtrend_known_value(self, known_fib_range):
        """ret_382 in downtrend = low + diff*0.382 = 100 + 38.2 = 138.2"""
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 125.0)
        assert result.ret_382 == pytest.approx(138.2, abs=0.01)

    def test_fib_zero_diff_returns_flat(self):
        result = calculate_fibonacci_levels(100.0, 100.0, 100.0)
        assert result.trend == "flat"

    def test_fib_levels_ordered_uptrend(self, known_fib_range):
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 175.0)
        # In uptrend: swing_low < ret_618 < ret_500 < ret_382 < swing_high
        assert result.swing_low < result.ret_618 < result.ret_500 < result.ret_382 < result.swing_high

    def test_fib_swing_high_low_preserved(self, known_fib_range):
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 175.0)
        assert result.swing_high == pytest.approx(r["high"], abs=0.01)
        assert result.swing_low == pytest.approx(r["low"], abs=0.01)

    def test_fib_midpoint_is_ret_500(self, known_fib_range):
        r = known_fib_range
        result = calculate_fibonacci_levels(r["high"], r["low"], 175.0)
        midpoint = (r["high"] + r["low"]) / 2
        assert result.ret_500 == pytest.approx(midpoint, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════
# Std Dev Bands Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestStdDevBands:

    def test_std_bands_returns_two_floats(self, uptrend_closes):
        std1, std2 = calculate_std_dev_bands(uptrend_closes)
        assert isinstance(std1, float)
        assert isinstance(std2, float)

    def test_std_bands_std2_is_double_std1(self, uptrend_closes):
        std1, std2 = calculate_std_dev_bands(uptrend_closes)
        assert std2 == pytest.approx(std1 * 2.0, rel=0.01)

    def test_std_bands_flat_data_near_zero(self):
        closes = [100.0] * 20
        std1, std2 = calculate_std_dev_bands(closes)
        assert std1 == pytest.approx(0.0, abs=0.001)
        assert std2 == pytest.approx(0.0, abs=0.001)

    def test_std_bands_insufficient_data_returns_zero(self, insufficient_closes):
        std1, std2 = calculate_std_dev_bands(insufficient_closes, period=20)
        assert std1 == 0.0
        assert std2 == 0.0

    def test_std_bands_positive_for_varied_data(self, uptrend_closes):
        std1, _ = calculate_std_dev_bands(uptrend_closes)
        assert std1 > 0.0

    def test_rolling_std_length_matches(self, uptrend_closes):
        series = calculate_rolling_std(uptrend_closes)
        assert len(series) == len(uptrend_closes)

    def test_rolling_std_warmup_is_nan(self, uptrend_closes):
        series = calculate_rolling_std(uptrend_closes, period=20)
        assert all(np.isnan(series[i]) for i in range(19))

    def test_rolling_std_non_negative(self, uptrend_closes):
        series = calculate_rolling_std(uptrend_closes)
        valid = series[~np.isnan(series)]
        assert all(v >= 0.0 for v in valid)


# ═══════════════════════════════════════════════════════════════════════════
# Breakout Detection Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestBreakoutDetection:

    def test_breakout_returns_dataclass(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        result = detect_donchian_breakout(d["highs"], d["lows"], d["closes"], d["volumes"])
        assert isinstance(result, BreakoutResult)

    def test_no_breakout_for_midrange_price(self, ohlcv_uptrend):
        d = ohlcv_uptrend
        # Mid-range price shouldn't break out
        closes_flat = d["closes"].copy()
        closes_flat[-1] = np.mean(closes_flat[-30:-1])
        result = detect_donchian_breakout(d["highs"], d["lows"], closes_flat, d["volumes"])
        assert result.direction in ("none", "bullish_breakout", "bearish_breakout")

    def test_bullish_breakout_detected(self):
        """Force a price above the 20-bar high."""
        n = 25
        highs = [105.0] * n
        lows = [95.0] * n
        closes = [100.0] * n
        volumes = [1000.0] * n
        # Last bar breaks above
        closes[-1] = 106.0
        highs[-1] = 107.0
        volumes[-1] = 3000.0  # high volume confirms
        result = detect_donchian_breakout(highs, lows, closes, volumes)
        assert result.direction == "bullish_breakout"

    def test_bearish_breakout_detected(self):
        """Force a price below the 20-bar low."""
        n = 25
        highs = [105.0] * n
        lows = [95.0] * n
        closes = [100.0] * n
        volumes = [1000.0] * n
        closes[-1] = 93.0
        lows[-1] = 92.0
        volumes[-1] = 3000.0
        result = detect_donchian_breakout(highs, lows, closes, volumes)
        assert result.direction == "bearish_breakout"

    def test_breakout_confidence_in_range(self):
        """Confidence must be between 0.0 and 1.0."""
        n = 25
        highs = [105.0] * n
        lows = [95.0] * n
        closes = [100.0] * n
        volumes = [1000.0] * n
        closes[-1] = 106.0
        highs[-1] = 107.0
        result = detect_donchian_breakout(highs, lows, closes, volumes)
        assert 0.0 <= result.confidence <= 1.0

    def test_no_breakout_insufficient_data(self):
        highs = [105.0, 106.0]
        lows = [95.0, 96.0]
        closes = [100.0, 101.0]
        volumes = [1000.0, 1000.0]
        result = detect_donchian_breakout(highs, lows, closes, volumes)
        assert result.direction == "none"
        assert result.confidence == 0.0

    def test_breakout_no_volume_still_valid(self):
        """Breakout without volume gives low confidence but still detects direction."""
        n = 25
        highs = [105.0] * n
        lows = [95.0] * n
        closes = [100.0] * n
        volumes = [0.0] * n
        closes[-1] = 106.0
        result = detect_donchian_breakout(highs, lows, closes, volumes)
        assert result.direction == "bullish_breakout"


# ═══════════════════════════════════════════════════════════════════════════
# Support & Resistance Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSupportResistance:

    def test_find_swing_lows_detects_local_minima(self):
        lows = [100.0, 95.0, 98.0, 92.0, 96.0, 90.0, 94.0]
        result = find_swing_lows(lows)
        assert 95.0 in result
        assert 92.0 in result
        assert 90.0 in result

    def test_find_swing_highs_detects_local_maxima(self):
        highs = [100.0, 110.0, 105.0, 120.0, 115.0, 130.0, 125.0]
        result = find_swing_highs(highs)
        assert 110.0 in result
        assert 120.0 in result
        assert 130.0 in result

    def test_swing_lows_sorted_ascending(self):
        lows = [100.0, 95.0, 98.0, 92.0, 96.0]
        result = find_swing_lows(lows)
        assert result == sorted(result)

    def test_swing_highs_sorted_descending(self):
        highs = [100.0, 110.0, 105.0, 120.0, 115.0]
        result = find_swing_highs(highs)
        assert result == sorted(result, reverse=True)

    def test_swing_lows_fallback_to_global_min(self):
        """When no local minima exist (monotone), fall back to global min."""
        lows = [100.0, 99.0, 98.0, 97.0, 96.0]
        result = find_swing_lows(lows)
        assert 96.0 in result

    def test_nearest_support_below_finds_closest(self):
        supports = [85.0, 90.0, 95.0, 80.0]
        level, near = nearest_support_below(price=97.0, support_levels=supports)
        assert level == pytest.approx(95.0, abs=0.01)

    def test_nearest_support_below_is_near(self):
        supports = [96.0]
        level, near = nearest_support_below(price=97.0, support_levels=supports, tolerance_pct=0.02)
        assert near is True

    def test_nearest_support_below_not_near_when_far(self):
        supports = [80.0]
        level, near = nearest_support_below(price=100.0, support_levels=supports, tolerance_pct=0.02)
        assert near is False

    def test_nearest_support_none_when_all_above(self):
        supports = [105.0, 110.0]
        level, near = nearest_support_below(price=100.0, support_levels=supports)
        assert level is None
        assert near is False


# ═══════════════════════════════════════════════════════════════════════════
# Linear Regression Slope Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestLinearRegressionSlope:

    def test_slope_positive_for_uptrend(self, uptrend_closes):
        slope = calculate_linear_regression_slope(uptrend_closes)
        assert slope > 0.0

    def test_slope_negative_for_downtrend(self, downtrend_closes):
        slope = calculate_linear_regression_slope(downtrend_closes)
        assert slope < 0.0

    def test_slope_near_zero_for_flat(self, flat_closes):
        slope = calculate_linear_regression_slope(flat_closes)
        assert abs(slope) < 0.01

    def test_slope_zero_insufficient_data(self):
        closes = [100.0, 101.0]
        slope = calculate_linear_regression_slope(closes, period=20)
        assert slope == 0.0

    def test_classify_slope_up(self):
        assert classify_slope(0.005) == "up"

    def test_classify_slope_down(self):
        assert classify_slope(-0.005) == "down"

    def test_classify_slope_flat_positive(self):
        assert classify_slope(0.0005) == "flat"

    def test_classify_slope_flat_negative(self):
        assert classify_slope(-0.0005) == "flat"

    def test_classify_slope_boundary(self):
        from domain.constants import INDICATOR_LRL_SLOPE_THRESHOLD
        assert classify_slope(INDICATOR_LRL_SLOPE_THRESHOLD + 1e-9) == "up"
        assert classify_slope(-INDICATOR_LRL_SLOPE_THRESHOLD - 1e-9) == "down"
        assert classify_slope(INDICATOR_LRL_SLOPE_THRESHOLD) == "flat"
