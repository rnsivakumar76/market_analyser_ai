import pytest
import pandas as pd
import numpy as np


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
