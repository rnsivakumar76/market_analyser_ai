import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch


@pytest.fixture
def sample_daily_data():
    """Generates 100 days of mock daily data."""
    dates = pd.date_range(start="2026-01-01", periods=100, freq='B')
    df = pd.DataFrame({
        'Open': np.linspace(100, 150, 100),
        'High': np.linspace(105, 155, 100),
        'Low': np.linspace(95, 145, 100),
        'Close': np.linspace(102, 152, 100),
        'Volume': np.random.randint(1000, 5000, 100)
    }, index=dates)
    return df


@pytest.fixture
def xau_ohlcv():
    """Realistic XAU/USD hourly OHLCV — current price ~5382, entry zone ~5277."""
    np.random.seed(42)
    dates = pd.date_range(start="2026-02-01", periods=300, freq='h')
    base = np.linspace(5200, 5400, 300) + np.random.normal(0, 8, 300)
    df = pd.DataFrame({
        'Open':  base - 3,
        'High':  base + 10,
        'Low':   base - 10,
        'Close': base + 2,
        'Volume': np.random.randint(500, 3000, 300),
    }, index=dates)
    return df


@pytest.fixture
def wti_ohlcv():
    """Realistic WTI hourly OHLCV — current price ~71.64, entry zone ~66.26."""
    np.random.seed(7)
    dates = pd.date_range(start="2026-02-01", periods=300, freq='h')
    base = np.linspace(65, 73, 300) + np.random.normal(0, 0.5, 300)
    df = pd.DataFrame({
        'Open':  base - 0.2,
        'High':  base + 0.8,
        'Low':   base - 0.8,
        'Close': base + 0.1,
        'Volume': np.random.randint(200, 1500, 300),
    }, index=dates)
    return df


@pytest.fixture
def pivot_points_bullish():
    """Mock PivotPoints Pydantic model — bullish layout (price above pivot)."""
    from app.models import PivotPoints
    return PivotPoints(pivot=70.0, r1=72.5, r2=74.0, r3=76.0, s1=68.0, s2=66.5, s3=65.0)


@pytest.fixture
def fibonacci_bullish():
    """Mock FibonacciLevels anchored to a bullish swing."""
    from app.models import FibonacciLevels
    return FibonacciLevels(
        trend="bullish", swing_high=75.0, swing_low=63.0,
        ret_382=68.41, ret_500=69.0, ret_618=69.59,
        ext_1272=78.27, ext_1618=82.41
    )


@pytest.fixture
def technical_analysis_bullish(pivot_points_bullish, fibonacci_bullish):
    """Mock TechnicalAnalysis for a bullish signal."""
    from app.models import TechnicalAnalysis
    return TechnicalAnalysis(
        pivot_points=pivot_points_bullish,
        fibonacci=fibonacci_bullish,
        least_resistance_line="up",
        trend_breakout="none",
        breakout_confidence=0.0,
        description="Bullish structure above pivot. S1=68.00, R1=72.50.",
    )


@pytest.fixture
def or_data_bearish():
    """ORB data: opening range broken bearish (intraday pullback)."""
    return {"or_high": 72.0, "or_low": 70.5, "broken": "bearish"}


@pytest.fixture
def or_data_bullish():
    """ORB data: opening range broken bullish."""
    return {"or_high": 72.0, "or_low": 70.5, "broken": "bullish"}


@pytest.fixture
def or_data_none():
    """ORB data: no breakout yet."""
    return {"or_high": 72.0, "or_low": 70.5, "broken": "none"}


@pytest.fixture
def strategy_settings_default():
    """Default StrategySettings used across multiple tests."""
    from app.models import StrategySettings
    return StrategySettings()


@pytest.fixture
def bullish_trend():
    from app.models import TrendAnalysis, Signal
    return TrendAnalysis(
        direction=Signal.BULLISH, fast_ma=100.0, slow_ma=90.0,
        price_above_fast_ma=True, price_above_slow_ma=True, description="test"
    )


@pytest.fixture
def bearish_trend():
    from app.models import TrendAnalysis, Signal
    return TrendAnalysis(
        direction=Signal.BEARISH, fast_ma=90.0, slow_ma=100.0,
        price_above_fast_ma=False, price_above_slow_ma=False, description="test"
    )


@pytest.fixture
def xau_ohlcv_daily():
    """300 days of XAU/USD daily data in an uptrend, suitable for LONG_TERM analysis."""
    np.random.seed(99)
    dates = pd.date_range(start="2025-01-01", periods=300, freq="D")
    base = np.linspace(1800, 2100, 300) + np.random.normal(0, 12, 300)
    return pd.DataFrame({
        "Open":   base - 4,
        "High":   base + 14,
        "Low":    base - 14,
        "Close":  base + 2,
        "Volume": np.random.randint(2000, 8000, 300),
    }, index=dates)


@pytest.fixture
def mock_twelvedata_fetcher():
    """TwelveDataFetcher with all network calls mocked out."""
    with patch("app.twelvedata_fetcher.TDClient") as MockClient:
        MockClient.return_value = MagicMock()
        from app.twelvedata_fetcher import TwelveDataFetcher
        f = TwelveDataFetcher(api_key="TEST_KEY_FAKE")
        yield f
