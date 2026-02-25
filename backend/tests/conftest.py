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
