import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

"""
Shared fixtures for domain layer unit tests.

All fixtures produce primitive types (lists, floats, ints) — no pandas, no Pydantic.
"""

import pytest
import numpy as np


# ── Price Series Factories ──────────────────────────────────────────────────

@pytest.fixture
def uptrend_closes():
    """100 closing prices in a steady uptrend (100 → 200)."""
    return list(np.linspace(100.0, 200.0, 100))


@pytest.fixture
def downtrend_closes():
    """100 closing prices in a steady downtrend (200 → 100)."""
    return list(np.linspace(200.0, 100.0, 100))


@pytest.fixture
def flat_closes():
    """100 closing prices with tiny random noise around 150."""
    np.random.seed(0)
    return list(np.full(100, 150.0) + np.random.normal(0, 0.01, 100))


@pytest.fixture
def volatile_closes():
    """50 bars of highly volatile prices (zigzag ±10)."""
    closes = []
    price = 100.0
    for i in range(50):
        price += 10.0 if i % 2 == 0 else -9.0
        closes.append(price)
    return closes


@pytest.fixture
def ohlcv_uptrend():
    """OHLCV arrays for 100-bar uptrend, roughly consistent spreads."""
    np.random.seed(42)
    closes = np.linspace(100.0, 200.0, 100)
    highs = closes + np.abs(np.random.normal(2.0, 0.5, 100))
    lows = closes - np.abs(np.random.normal(2.0, 0.5, 100))
    opens = closes - np.random.normal(0.5, 0.3, 100)
    volumes = np.random.randint(1000, 5000, 100).astype(float)
    return {
        "highs": list(highs),
        "lows": list(lows),
        "closes": list(closes),
        "opens": list(opens),
        "volumes": list(volumes),
    }


@pytest.fixture
def ohlcv_downtrend():
    """OHLCV arrays for 100-bar downtrend."""
    np.random.seed(7)
    closes = np.linspace(200.0, 100.0, 100)
    highs = closes + np.abs(np.random.normal(2.0, 0.5, 100))
    lows = closes - np.abs(np.random.normal(2.0, 0.5, 100))
    volumes = np.random.randint(1000, 5000, 100).astype(float)
    return {
        "highs": list(highs),
        "lows": list(lows),
        "closes": list(closes),
        "volumes": list(volumes),
    }


@pytest.fixture
def no_volume_ohlcv():
    """OHLCV for a Forex/commodity instrument with zero volume."""
    closes = list(np.linspace(100.0, 150.0, 60))
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    volumes = [0.0] * 60
    return {"highs": highs, "lows": lows, "closes": closes, "volumes": volumes}


@pytest.fixture
def insufficient_closes():
    """Only 5 closes — too few for most calculations."""
    return [100.0, 101.0, 102.0, 101.5, 103.0]


# ── Known-Value Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def known_pivot_bar():
    """Single bar with known H/L/C for pivot point verification."""
    return {"high": 110.0, "low": 90.0, "close": 100.0}
    # pivot = (110+90+100)/3 = 100.0
    # r1 = 200 - 90 = 110.0
    # s1 = 200 - 110 = 90.0
    # r2 = 100 + 20 = 120.0
    # s2 = 100 - 20 = 80.0


@pytest.fixture
def known_fib_range():
    """Swing high/low for verifiable Fibonacci levels."""
    return {"high": 200.0, "low": 100.0}
    # diff = 100
    # uptrend ret_382 = 200 - 38.2 = 161.8
    # uptrend ret_618 = 200 - 61.8 = 138.2
    # uptrend ext_1618 = 100 + 161.8 = 261.8
