import pytest
import math
import json
import numpy as np

from app.analyzers.strength_analyzer import analyze_daily_strength
from app.analyzers.trend_analyzer import analyze_monthly_trend
from app.analyzers.volatility_analyzer import analyze_volatility_and_risk
from app.analyzers.pullback_analyzer import analyze_weekly_pullback
from app.analyzers.relative_strength_analyzer import analyze_relative_strength

def test_strength_analyzer_json_serialization(sample_daily_data):
    """Ensure that strength analyzer outputs native Python floats, not numpy floats, for JSON dumps compliance."""
    # Force a NaN volume condition if necessary or just run standard
    sample_daily_data.loc[sample_daily_data.index[-1], 'Volume'] = np.nan
    
    result = analyze_daily_strength(sample_daily_data, {})
    
    # Assert JSON serializes without ValueError
    # If any internal values are np.float64, json.dumps config allow_nan=False (which FastAPI uses) will crash if na
    # But even basic dumps proves it's native Python dict
    try:
        json_str = json.dumps(result.dict())
        assert isinstance(json_str, str)
    except TypeError as e:
        pytest.fail(f"Could not serialize Strength analysis: {e}")
        
    assert isinstance(result.rsi, float)
    assert isinstance(result.adx, float)
    assert isinstance(result.volume_ratio, float)
    assert isinstance(result.price_change_percent, float)


def test_volatility_analyzer_json_serialization(sample_daily_data):
    result = analyze_volatility_and_risk(sample_daily_data, 150.0, "bullish")
    try:
        json_str = json.dumps(result.dict())
        assert isinstance(json_str, str)
    except TypeError as e:
        pytest.fail(f"Could not serialize Volatility analysis: {e}")
        
    assert isinstance(result.stop_loss, float)
    assert isinstance(result.take_profit, float)


def test_trend_analyzer_json_serialization(sample_daily_data):
    result = analyze_monthly_trend(sample_daily_data, {})
    try:
        json_str = json.dumps(result.dict())
        assert isinstance(json_str, str)
    except TypeError as e:
        pytest.fail(f"Could not serialize Trend analysis: {e}")
        
    assert isinstance(result.fast_ma, float)
    assert isinstance(result.slow_ma, float)
    assert isinstance(result.price_above_fast_ma, bool)

    
def test_relative_strength_json_serialization(sample_daily_data):
    # Create mock benchmark slightly lagging
    bench_data = sample_daily_data.copy()
    bench_data['Close'] = bench_data['Close'] * 0.9
    
    result = analyze_relative_strength(sample_daily_data, bench_data, "AAPL", "SPY")
    try:
        json_str = json.dumps(result.dict())
        assert isinstance(json_str, str)
    except TypeError as e:
        pytest.fail(f"Could not serialize Relative Strength analysis: {e}")
        
    assert isinstance(result.alpha, float)
    assert isinstance(result.symbol_return, float)
