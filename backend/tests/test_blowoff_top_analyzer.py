import pandas as pd

from app.analyzers.blowoff_top_analyzer import analyze_blowoff_top
from app.models import TechnicalAnalysis, PivotPoints, FibonacciLevels, VolatilityAnalysis


def _tech(rsi_divergence: str = "bearish") -> TechnicalAnalysis:
    return TechnicalAnalysis(
        pivot_points=PivotPoints(pivot=100.0, r1=105.0, r2=110.0, r3=115.0, s1=95.0, s2=90.0, s3=85.0),
        fibonacci=FibonacciLevels(
            trend="up",
            swing_high=115.0,
            swing_low=85.0,
            ret_382=96.0,
            ret_500=100.0,
            ret_618=103.0,
            ext_1272=121.0,
            ext_1618=128.0,
        ),
        least_resistance_line="up",
        trend_breakout="none",
        breakout_confidence=0.0,
        rsi_divergence=rsi_divergence,
        description="test",
    )


def _vol(atr_pct: float = 85.0) -> VolatilityAnalysis:
    return VolatilityAnalysis(
        atr=2.0,
        stop_loss=95.0,
        take_profit=115.0,
        risk_reward_ratio=2.5,
        description="test",
        atr_percentile_rank=atr_pct,
    )


def _oil_df() -> pd.DataFrame:
    # 40 bars with sharp late acceleration then failed breakout and breakdown.
    closes = [80 + i * 0.8 for i in range(30)] + [106, 110, 114, 118, 123, 128, 134, 131, 126, 120]
    highs = [c + 2 for c in closes]
    lows = [c - 2 for c in closes]
    opens = [closes[0]] + closes[:-1]
    volume = [1000] * len(closes)
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="D")
    return pd.DataFrame(
        {
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volume,
        },
        index=idx,
    )


def test_non_oil_symbol_returns_not_applicable():
    result = analyze_blowoff_top("AAPL", _oil_df(), technical_indicators=_tech(), volatility=_vol())
    assert result.applicable is False
    assert result.phase == "normal"


def test_oil_blowoff_detects_and_arms_or_triggers():
    result = analyze_blowoff_top("WTI", _oil_df(), technical_indicators=_tech(), volatility=_vol())
    assert result.applicable is True
    assert result.blowoff_score >= 60
    assert result.phase in {"blowoff", "confirmed_breakdown"}
    assert result.entry_state in {"armed", "triggered"}
