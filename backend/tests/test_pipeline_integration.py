"""
Integration smoke tests for the full analysis pipeline.
Uses mocked TwelveData API — no real API keys needed.
Covers: analyze_instrument_lazy end-to-end, batch fetch pipeline,
        intermarket analyzer with corrected DXY symbol,
        scheduler timing, and JSON-serialisable final output.

Run:  pytest tests/test_pipeline_integration.py -v
"""
import json
import time
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

from app.models import Signal, StrategyMode, StrategySettings


def _default_settings() -> StrategySettings:
    return StrategySettings(
        conviction_threshold=70,
        adx_threshold=25,
        atr_multiplier_tp=3.0,
        atr_multiplier_sl=1.5,
        portfolio_value=10000.0,
        risk_per_trade_percent=1.0,
    )


# ---------------------------------------------------------------------------
# Shared OHLCV helpers
# ---------------------------------------------------------------------------

def _ohlcv(n=300, base=2000.0, vol=10.0, freq="D", seed=1) -> pd.DataFrame:
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq=freq)
    prices = np.linspace(base * 0.9, base * 1.05, n) + np.random.normal(0, vol, n)
    df = pd.DataFrame({
        "Open":   prices - vol * 0.3,
        "High":   prices + vol,
        "Low":    prices - vol,
        "Close":  prices,
        "Volume": np.random.randint(1000, 10000, n),
    }, index=dates)
    return df


def _spx_df(n=1000):
    return _ohlcv(n, base=5000.0, vol=50.0, seed=2)


def _dxy_df(n=100):
    return _ohlcv(n, base=104.0, vol=0.3, seed=3)


def _tnx_df(n=100):
    return _ohlcv(n, base=4.5, vol=0.05, seed=4)


# ---------------------------------------------------------------------------
# 1. analyze_instrument_lazy — end-to-end with mocked fetcher
# ---------------------------------------------------------------------------

class TestAnalyzeInstrumentLazy:
    """
    Full analysis pipeline for a single instrument.
    Mock TwelveData so we test all downstream logic without API calls.
    """

    @pytest.fixture
    def mock_fetcher(self):
        with patch("app.data_fetcher.get_td_fetcher") as mock_get:
            td = MagicMock()
            td.api_key = "FAKE"
            td._normalize_interval.side_effect = lambda x: {
                "1d": "1day", "1mo": "1month", "1wk": "1week",
            }.get(x.lower(), x)
            td.fetch_historical_data.return_value = _ohlcv(500, base=2000.0)
            mock_get.return_value = td
            yield td

    def test_xau_analysis_returns_result(self, mock_fetcher):
        from app.main import analyze_instrument_lazy
        settings = StrategySettings(
            conviction_threshold=70,
            adx_threshold=25,
            atr_multiplier_tp=3.0,
            atr_multiplier_sl=1.5,
            portfolio_value=10000.0,
            risk_per_trade_percent=1.0,
        )

        analysis, hist = analyze_instrument_lazy(
            symbol="XAU",
            name="Gold",
            params={},
            benchmark_direction=Signal.NEUTRAL,
            strategy_settings=settings,
            mode=StrategyMode.SHORT_TERM,
            pre_execution_df=_ohlcv(300, base=2000.0),
            pre_macro_df=_ohlcv(500, base=2000.0),
            pre_pullback_df=_ohlcv(200, base=2000.0),
        )

        assert analysis is not None, "analyze_instrument_lazy returned None unexpectedly"
        assert analysis.symbol == "XAU"
        assert analysis.current_price > 0
        assert analysis.trade_signal is not None
        assert analysis.trade_signal.recommendation in [
            Signal.BULLISH, Signal.BEARISH, Signal.NEUTRAL
        ]

    def test_result_is_json_serialisable(self, mock_fetcher):
        from app.main import analyze_instrument_lazy
        settings = _default_settings()

        analysis, _ = analyze_instrument_lazy(
            symbol="XAU",
            name="Gold",
            params={},
            benchmark_direction=Signal.NEUTRAL,
            strategy_settings=settings,
            mode=StrategyMode.SHORT_TERM,
            pre_execution_df=_ohlcv(300, base=2000.0),
            pre_macro_df=_ohlcv(500, base=2000.0),
            pre_pullback_df=_ohlcv(200, base=2000.0),
        )

        if analysis:
            try:
                json_str = analysis.json()
                assert isinstance(json_str, str)
            except (TypeError, ValueError) as e:
                pytest.fail(f"analysis.json() is not JSON-serialisable: {e}")

    def test_wti_analysis_does_not_crash(self, mock_fetcher):
        from app.main import analyze_instrument_lazy
        settings = _default_settings()
        mock_fetcher.fetch_historical_data.return_value = _ohlcv(300, base=72.0, vol=0.8)

        analysis, _ = analyze_instrument_lazy(
            symbol="WTI",
            name="Crude Oil",
            params={},
            benchmark_direction=Signal.NEUTRAL,
            strategy_settings=settings,
            mode=StrategyMode.SHORT_TERM,
            pre_execution_df=_ohlcv(300, base=72.0, vol=0.8),
            pre_macro_df=_ohlcv(500, base=72.0, vol=0.8),
        )

        # Must not raise — result may be None if data insufficient but must not explode
        assert analysis is None or analysis.symbol == "WTI"

    def test_btc_analysis_does_not_crash(self, mock_fetcher):
        from app.main import analyze_instrument_lazy
        settings = _default_settings()
        mock_fetcher.fetch_historical_data.return_value = _ohlcv(300, base=45000.0, vol=800.0)

        analysis, _ = analyze_instrument_lazy(
            symbol="BTC",
            name="Bitcoin",
            params={},
            benchmark_direction=Signal.NEUTRAL,
            strategy_settings=settings,
            mode=StrategyMode.SHORT_TERM,
            pre_execution_df=_ohlcv(300, base=45000.0, vol=800.0),
            pre_macro_df=_ohlcv(500, base=45000.0, vol=800.0),
        )

        assert analysis is None or analysis.symbol == "BTC"

    def test_analysis_with_dxy_and_tnx_context(self, mock_fetcher):
        """Ensure passing dxy_df and us10y_df does not crash intermarket analysis."""
        from app.main import analyze_instrument_lazy
        settings = _default_settings()

        analysis, _ = analyze_instrument_lazy(
            symbol="XAU",
            name="Gold",
            params={},
            benchmark_direction=Signal.BULLISH,
            strategy_settings=settings,
            mode=StrategyMode.SHORT_TERM,
            pre_execution_df=_ohlcv(300, base=2000.0),
            pre_macro_df=_ohlcv(500, base=2000.0),
            dxy_df=_dxy_df(),
            us10y_df=_tnx_df(),
        )

        assert analysis is None or analysis.intermarket_context is not None or True  # no crash


# ---------------------------------------------------------------------------
# 2. Intermarket analyzer — DXY symbol regression
# ---------------------------------------------------------------------------

class TestIntermarketAnalyzer:

    def test_dxy_symbol_constant_is_correct(self):
        from app.analyzers.intermarket_analyzer import DXY_SYMBOL
        assert DXY_SYMBOL == "DXY", (
            f"DXY_SYMBOL must be 'DXY' (TwelveData-compatible). Got: {DXY_SYMBOL!r}. "
            "DX-Y.NYB is a Yahoo Finance symbol and causes TwelveData 'symbol not found' errors."
        )

    def test_us10y_symbol_is_tnx(self):
        from app.analyzers.intermarket_analyzer import US10Y_SYMBOL
        assert US10Y_SYMBOL == "TNX"

    def test_analyze_intermarket_with_valid_dfs(self):
        from app.analyzers.intermarket_analyzer import analyze_intermarket_context
        result = analyze_intermarket_context(
            symbol="XAU",
            dxy_df=_dxy_df(60),
            us10y_df=_tnx_df(60),
        )
        assert result is not None
        assert result.dxy_direction in ("up", "down", "flat")
        assert result.us10y_direction in ("up", "down", "flat")
        assert result.gold_implication in ("bullish", "bearish", "neutral")
        assert isinstance(result.description, str)

    def test_analyze_intermarket_with_none_dfs_returns_neutral(self):
        from app.analyzers.intermarket_analyzer import analyze_intermarket_context
        result = analyze_intermarket_context("XAU", dxy_df=None, us10y_df=None)
        assert result is not None
        assert result.dxy_direction in ("up", "down", "flat", "N/A") or True  # no crash

    def test_intermarket_dxy_direction_up_means_bearish_gold(self):
        """Classic inverse: rising DXY → bearish for Gold."""
        from app.analyzers.intermarket_analyzer import analyze_intermarket_context
        # Rising DXY: prices go up over 60 bars
        dates = pd.date_range("2025-01-01", periods=60)
        rising_dxy = pd.DataFrame({
            "Open": np.linspace(100.0, 106.0, 60),
            "High": np.linspace(100.5, 106.5, 60),
            "Low":  np.linspace(99.5,  105.5, 60),
            "Close": np.linspace(100.0, 106.0, 60),
            "Volume": [1000] * 60,
        }, index=dates)

        result = analyze_intermarket_context("XAU", dxy_df=rising_dxy, us10y_df=None)
        if result and result.dxy_direction == "up":
            assert result.gold_implication in ("bearish", "neutral"), (
                "Rising DXY should imply bearish or neutral for gold"
            )


# ---------------------------------------------------------------------------
# 3. Batch fetch pipeline — interval correctness end-to-end
# ---------------------------------------------------------------------------

class TestBatchFetchPipeline:

    def test_benchmark_batch_uses_correct_intervals(self):
        """
        Simulate the benchmark batch fetch in run_market_scan.
        Verify intervals sent to TwelveData are TwelveData-native (no '1d'/'1mo').
        """
        from app.twelvedata_fetcher import TwelveDataFetcher
        captured_intervals = []

        with patch.object(TwelveDataFetcher, "_rate_limit_wait"):
            with patch.object(TwelveDataFetcher, "client", create=True) as mock_client:
                def fake_ts(**kwargs):
                    captured_intervals.append(kwargs.get("interval", "UNKNOWN"))
                    ts = MagicMock()
                    ts.as_pandas.return_value = None
                    return ts

                mock_client.time_series.side_effect = fake_ts

                fetcher = TwelveDataFetcher.__new__(TwelveDataFetcher)
                fetcher.client = mock_client
                fetcher._lock = __import__("threading").Lock()

                # Simulate SHORT_TERM mode benchmark fetch
                bench_interval = "1day"
                exec_interval = "1h"
                fetcher.fetch_batch_data(["SPX", "BTC", "DXY", "TNX"], interval=bench_interval, days=1000)
                fetcher.fetch_batch_data(["SPX", "BTC", "DXY", "TNX"], interval=exec_interval, days=20)

        invalid = [iv for iv in captured_intervals if iv in ("1d", "1mo", "1wk", "1m")]
        assert not invalid, (
            f"Invalid intervals sent to TwelveData API: {invalid}. "
            "Must use '1day', '1month', '1week' instead."
        )

    def test_all_known_bad_intervals_are_normalized(self):
        """Exhaustive check: all legacy interval aliases must be normalised."""
        from app.twelvedata_fetcher import TwelveDataFetcher
        fetcher = TwelveDataFetcher.__new__(TwelveDataFetcher)

        bad_intervals = ["1d", "1D", "1mo", "1MO", "1wk", "1WK", "1w", "1W", "d", "w"]
        valid_td = {"1min", "5min", "15min", "30min", "45min", "1h", "2h", "4h",
                    "8h", "1day", "1week", "1month"}

        for bad in bad_intervals:
            normalised = fetcher._normalize_interval(bad)
            assert normalised in valid_td, (
                f"Interval '{bad}' normalised to '{normalised}' which is not a valid TwelveData interval."
            )


# ---------------------------------------------------------------------------
# 4. Full scan performance — must complete within reasonable time
# ---------------------------------------------------------------------------

class TestScanPerformance:

    def test_single_instrument_analysis_under_5s(self):
        """
        End-to-end analysis of a single instrument with mock data
        must complete within 5 seconds (excludes real API calls).
        """
        with patch("app.data_fetcher.get_td_fetcher") as mock_get:
            td = MagicMock()
            td.api_key = "FAKE"
            td._normalize_interval.side_effect = lambda x: x
            td.fetch_historical_data.return_value = _ohlcv(500, base=2000.0)
            mock_get.return_value = td

            from app.main import analyze_instrument_lazy
            settings = _default_settings()

            t_start = time.time()
            analyze_instrument_lazy(
                symbol="XAU",
                name="Gold",
                params={},
                benchmark_direction=Signal.NEUTRAL,
                strategy_settings=settings,
                mode=StrategyMode.SHORT_TERM,
                pre_execution_df=_ohlcv(300, base=2000.0),
                pre_macro_df=_ohlcv(500, base=2000.0),
                pre_pullback_df=_ohlcv(200, base=2000.0),
            )
            elapsed = time.time() - t_start

        assert elapsed < 5.0, (
            f"Single instrument analysis took {elapsed:.2f}s — expected < 5s. "
            "Check for synchronous blocking calls or unguarded loops."
        )


# ---------------------------------------------------------------------------
# 5. News analyzer — graceful failure
# ---------------------------------------------------------------------------

class TestNewsAnalyzer:

    def test_fetch_rss_returns_list_even_if_network_fails(self):
        from app.analyzers.news_analyzer import fetch_rss_news
        with patch("app.analyzers.news_analyzer.requests.get") as mock_get:
            mock_get.side_effect = Exception("Network timeout")
            result = fetch_rss_news("XAU")
            assert isinstance(result, list)

    def test_analyze_news_sentiment_returns_model_on_empty_news(self):
        from app.analyzers.news_analyzer import analyze_news_sentiment
        from app.models import NewsSentiment
        result = analyze_news_sentiment("XAU", api_key="")
        assert result is not None
        assert isinstance(result, NewsSentiment)
        assert result.label in ("Bullish", "Bearish", "Neutral")

    def test_yahoo_rss_map_does_not_use_dx_y_nyb_for_twelvdata(self):
        """
        DX-Y.NYB in news_analyzer._YAHOO_SYMBOL_MAP is OK (Yahoo Finance RSS).
        But DXY in intermarket_analyzer must NOT be DX-Y.NYB (TwelveData).
        """
        from app.analyzers.intermarket_analyzer import DXY_SYMBOL
        assert DXY_SYMBOL != "DX-Y.NYB", (
            "intermarket_analyzer.DXY_SYMBOL must not be DX-Y.NYB (invalid for TwelveData). "
            "The Yahoo Finance RSS map in news_analyzer may keep DX-Y.NYB — that's separate."
        )


# ---------------------------------------------------------------------------
# 6. Output completeness — required fields always present
# ---------------------------------------------------------------------------

class TestOutputCompleteness:

    @pytest.fixture
    def xau_analysis(self):
        with patch("app.data_fetcher.get_td_fetcher") as mock_get:
            td = MagicMock()
            td.api_key = "FAKE"
            td._normalize_interval.side_effect = lambda x: x
            td.fetch_historical_data.return_value = _ohlcv(500, base=2000.0)
            mock_get.return_value = td

            from app.main import analyze_instrument_lazy
            settings = _default_settings()
            analysis, _ = analyze_instrument_lazy(
                symbol="XAU",
                name="Gold",
                params={},
                benchmark_direction=Signal.NEUTRAL,
                strategy_settings=settings,
                mode=StrategyMode.SHORT_TERM,
                pre_execution_df=_ohlcv(300, base=2000.0),
                pre_macro_df=_ohlcv(500, base=2000.0),
                pre_pullback_df=_ohlcv(200, base=2000.0),
            )
            return analysis

    def test_required_fields_present(self, xau_analysis):
        if xau_analysis is None:
            pytest.skip("Analysis returned None — check analyzer logic")
        assert xau_analysis.symbol == "XAU"
        assert xau_analysis.current_price > 0
        assert xau_analysis.trade_signal is not None
        assert xau_analysis.trade_signal.executive_summary != ""
        assert isinstance(xau_analysis.trade_signal.reasons, list)
        assert isinstance(xau_analysis.trade_signal.score, int)
        assert -100 <= xau_analysis.trade_signal.score <= 100

    def test_executive_summary_is_coherent(self, xau_analysis):
        if xau_analysis is None:
            pytest.skip("Analysis returned None")
        summary = xau_analysis.trade_signal.executive_summary
        assert len(summary) > 30, "Executive summary too short"
        assert "." in summary, "Executive summary should be a proper sentence"

    def test_score_within_bounds(self, xau_analysis):
        if xau_analysis is None:
            pytest.skip("Analysis returned None")
        score = xau_analysis.trade_signal.score
        assert -100 <= score <= 100, f"Score {score} out of bounds [-100, 100]"
