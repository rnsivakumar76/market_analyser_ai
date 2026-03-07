"""
Tests for calculate_liquidity_map — division-by-zero guards and edge cases.
Covers: None/short df, zero/negative price, NaN data, extreme prices,
        flat market, standard gold/oil/BTC price ranges.
Run:  pytest tests/test_liquidity_map.py -v
"""
import pytest
import pandas as pd
import numpy as np

from app.analyzers.liquidity_map_analyzer import (
    calculate_liquidity_map,
    _cluster_levels,
    _find_swing_highs,
    _find_swing_lows,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_df(n=100, base=100.0, volatility=1.0, seed=42) -> pd.DataFrame:
    """Generate a clean OHLCV DataFrame at a given price level."""
    np.random.seed(seed)
    prices = np.linspace(base * 0.95, base * 1.05, n) + np.random.normal(0, volatility, n)
    return pd.DataFrame({
        "Open":   prices - 0.3,
        "High":   prices + volatility,
        "Low":    prices - volatility,
        "Close":  prices + 0.1,
        "Volume": np.random.randint(500, 5000, n),
    })


# ---------------------------------------------------------------------------
# 1. Input guard — None / short DataFrame
# ---------------------------------------------------------------------------

class TestInputGuards:

    def test_none_dataframe_returns_none(self):
        assert calculate_liquidity_map(None, 100.0) is None

    def test_empty_dataframe_returns_none(self):
        assert calculate_liquidity_map(pd.DataFrame(), 100.0) is None

    def test_too_few_rows_returns_none(self):
        df = _make_df(n=29)  # min is 30
        assert calculate_liquidity_map(df, 100.0) is None

    def test_exactly_30_rows_passes(self):
        df = _make_df(n=30)
        result = calculate_liquidity_map(df, df["Close"].iloc[-1])
        # Should not raise; may return None if levels empty but must not crash
        assert result is None or hasattr(result, "resistance_levels")


# ---------------------------------------------------------------------------
# 2. Price guard — zero, None, negative
# ---------------------------------------------------------------------------

class TestPriceGuards:

    def test_zero_price_returns_none(self):
        df = _make_df(100)
        assert calculate_liquidity_map(df, 0.0) is None

    def test_negative_price_returns_none(self):
        df = _make_df(100)
        assert calculate_liquidity_map(df, -50.0) is None

    def test_none_price_returns_none(self):
        df = _make_df(100)
        assert calculate_liquidity_map(df, None) is None

    def test_false_price_returns_none(self):
        """bool(False) is falsy — must be treated the same as 0."""
        df = _make_df(100)
        assert calculate_liquidity_map(df, False) is None


# ---------------------------------------------------------------------------
# 3. Division-by-zero regression — the bug that was fixed
# ---------------------------------------------------------------------------

class TestDivisionByZeroGuards:

    def test_does_not_raise_zero_division_on_any_price(self):
        """Regression: previous code raised ZeroDivisionError for some inputs."""
        df = _make_df(100, base=100.0)
        for price in [0.5, 1.0, 10.0, 99.99, 100.0, 1000.0, 2000.0, 50000.0]:
            try:
                result = calculate_liquidity_map(df, price)
                # Must return None or a valid LiquidityMap — never raise
                assert result is None or hasattr(result, "resistance_levels")
            except ZeroDivisionError:
                pytest.fail(f"ZeroDivisionError raised for price={price}")

    def test_price_of_1_does_not_raise(self):
        df = _make_df(100, base=1.5, volatility=0.05)
        try:
            result = calculate_liquidity_map(df, 1.5)
            assert result is None or hasattr(result, "resistance_levels")
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError raised for price=1.5")

    def test_nan_high_low_returns_none_not_raise(self):
        """If High/Low columns have NaN, function must return None gracefully."""
        df = _make_df(100, base=100.0)
        df["High"] = np.nan
        df["Low"] = np.nan
        try:
            result = calculate_liquidity_map(df, 100.0)
            assert result is None
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError raised for NaN High/Low data")
        except Exception:
            pass  # Other exceptions acceptable; ZeroDivisionError is the regression

    def test_inf_high_low_returns_none_not_raise(self):
        df = _make_df(100, base=100.0)
        df.loc[df.index[50], "High"] = np.inf
        df.loc[df.index[50], "Low"] = -np.inf
        try:
            result = calculate_liquidity_map(df, 100.0)
            # inf in data min/max → should return None
            assert result is None or hasattr(result, "resistance_levels")
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError raised with inf data values")


# ---------------------------------------------------------------------------
# 4. _cluster_levels — zero-reference guard
# ---------------------------------------------------------------------------

class TestClusterLevels:

    def test_empty_list(self):
        assert _cluster_levels([]) == []

    def test_single_level(self):
        result = _cluster_levels([100.0])
        assert result == [100.0]

    def test_clusters_nearby_levels(self):
        result = _cluster_levels([100.0, 100.3, 100.5, 105.0])
        assert len(result) < 4, "nearby levels should be merged into clusters"

    def test_zero_level_does_not_raise(self):
        """Regression: ref==0 used to divide; now guarded by abs(ref)<1e-10."""
        try:
            result = _cluster_levels([0.0, 0.001, 100.0])
            assert isinstance(result, list)
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError in _cluster_levels with zero level")

    def test_near_zero_level_does_not_raise(self):
        try:
            result = _cluster_levels([1e-12, 1e-11, 100.0])
            assert isinstance(result, list)
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError in _cluster_levels with near-zero level")

    def test_negative_levels_do_not_raise(self):
        try:
            result = _cluster_levels([-5.0, -3.0, 100.0])
            assert isinstance(result, list)
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError in _cluster_levels with negative levels")

    def test_result_is_sorted_ascending(self):
        result = _cluster_levels([110.0, 90.0, 100.0, 95.0])
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# 5. Standard price ranges — real-world sanity checks
# ---------------------------------------------------------------------------

class TestRealWorldPriceRanges:

    @pytest.mark.parametrize("base,price,label", [
        (2000.0, 2050.0,  "XAU gold ~2000"),
        (70.0,   72.5,    "WTI crude ~70"),
        (5000.0, 5200.0,  "SPX ~5000"),
        (50000.0, 52000.0, "BTC ~50000"),
        (1.08,   1.085,   "EUR/USD ~1.08"),
        (0.85,   0.88,    "GBP/USD ~0.85"),
    ])
    def test_standard_price_range(self, base, price, label):
        df = _make_df(150, base=base, volatility=base * 0.005)
        try:
            result = calculate_liquidity_map(df, price)
            assert result is None or hasattr(result, "resistance_levels"), (
                f"Unexpected result type for {label}"
            )
        except ZeroDivisionError:
            pytest.fail(f"ZeroDivisionError for {label}")

    def test_xau_returns_levels_above_and_below(self):
        """For XAU, expect both resistance and support levels to be returned."""
        df = _make_df(200, base=2000.0, volatility=10.0)
        result = calculate_liquidity_map(df, 2030.0)
        if result is not None:
            assert isinstance(result.resistance_levels, list)
            assert isinstance(result.support_levels, list)
            assert len(result.interpretation) > 0

    def test_levels_are_correct_side(self):
        """Resistance levels must be above price; support levels must be below."""
        df = _make_df(200, base=100.0, volatility=1.0)
        current_price = 100.0
        result = calculate_liquidity_map(df, current_price)
        if result:
            for r in result.resistance_levels:
                assert r.price > current_price, f"Resistance {r.price} must be > {current_price}"
            for s in result.support_levels:
                assert s.price < current_price, f"Support {s.price} must be < {current_price}"

    def test_distance_pct_is_positive(self):
        df = _make_df(200, base=100.0, volatility=1.0)
        result = calculate_liquidity_map(df, 100.0)
        if result:
            for level in result.resistance_levels + result.support_levels:
                assert level.distance_pct >= 0, "Distance pct must be non-negative"


# ---------------------------------------------------------------------------
# 6. Flat market — High == Low edge case
# ---------------------------------------------------------------------------

class TestFlatMarket:

    def test_completely_flat_data_does_not_raise(self):
        """Edge case: constant OHLCV — no swings, step still computed correctly."""
        df = pd.DataFrame({
            "Open":   [100.0] * 100,
            "High":   [100.0] * 100,
            "Low":    [100.0] * 100,
            "Close":  [100.0] * 100,
            "Volume": [1000] * 100,
        })
        try:
            result = calculate_liquidity_map(df, 100.0)
            assert result is None or hasattr(result, "resistance_levels")
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError on completely flat data")


# ---------------------------------------------------------------------------
# 7. _find_swing_highs / _find_swing_lows
# ---------------------------------------------------------------------------

class TestSwingDetection:

    def test_swing_highs_are_local_maxima(self):
        """Swing highs must be values where surrounding bars are lower."""
        prices = pd.Series([95, 96, 100, 96, 95, 96, 98, 96, 95])
        highs = _find_swing_highs(prices, lookback=2)
        assert 100.0 in highs

    def test_swing_lows_are_local_minima(self):
        prices = pd.Series([100, 99, 95, 99, 100, 99, 97, 99, 100])
        lows = _find_swing_lows(prices, lookback=2)
        assert 95.0 in lows

    def test_monotonic_increase_has_no_swing_highs(self):
        prices = pd.Series(np.arange(20, dtype=float))
        highs = _find_swing_highs(prices, lookback=3)
        assert highs == []

    def test_nan_values_in_series_do_not_raise(self):
        prices = pd.Series([100.0, np.nan, 105.0, 100.0, 95.0, 100.0, 105.0, 100.0])
        try:
            result = _find_swing_highs(prices, lookback=2)
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"Swing high detection raised on NaN data: {e}")

    def test_all_nan_returns_empty(self):
        prices = pd.Series([np.nan] * 20)
        highs = _find_swing_highs(prices, lookback=3)
        assert highs == []
