"""
Tests for TwelveDataFetcher and data_fetcher robustness.
Covers: interval normalization, symbol mapping, batch-fetch guards,
        fallback logic, and data edge-cases.
Run:  pytest tests/test_fetcher_robustness.py -v
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock

from app.twelvedata_fetcher import TwelveDataFetcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fetcher():
    """TwelveDataFetcher with a mocked twelvedata client so no real API calls."""
    with patch("app.twelvedata_fetcher.TDClient") as MockClient:
        MockClient.return_value = MagicMock()
        f = TwelveDataFetcher(api_key="TEST_KEY_FAKE")
        yield f


def _make_ohlcv(n=100, start_price=100.0, symbol="XAU") -> pd.DataFrame:
    """Helper: create realistic OHLCV DataFrame."""
    np.random.seed(0)
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    base = np.linspace(start_price, start_price * 1.1, n) + np.random.normal(0, 1, n)
    return pd.DataFrame({
        "datetime": dates,
        "open":   base - 0.5,
        "high":   base + 1.0,
        "low":    base - 1.0,
        "close":  base + 0.2,
        "volume": np.random.randint(1000, 5000, n),
    })


# ---------------------------------------------------------------------------
# 1. Interval normalisation
# ---------------------------------------------------------------------------

class TestIntervalNormalization:
    """_normalize_interval must silently fix any non-TwelveData alias."""

    @pytest.mark.parametrize("raw,expected", [
        ("1d",    "1day"),
        ("1D",    "1day"),       # case-insensitive
        ("1mo",   "1month"),
        ("1MO",   "1month"),
        ("1wk",   "1week"),
        ("1WK",   "1week"),
        ("1w",    "1week"),
        ("d",     "1day"),
        ("w",     "1week"),
        # Pass-throughs — TwelveData native values must not change
        ("1day",   "1day"),
        ("1week",  "1week"),
        ("1month", "1month"),
        ("1h",     "1h"),
        ("4h",     "4h"),
        ("15min",  "15min"),
        ("30min",  "30min"),
    ])
    def test_normalize_interval(self, fetcher, raw, expected):
        assert fetcher._normalize_interval(raw) == expected

    def test_fetch_batch_normalizes_interval(self, fetcher):
        """fetch_batch_data must call the API with normalised interval, not '1d'."""
        captured = {}

        def fake_time_series(**kwargs):
            captured.update(kwargs)
            ts = MagicMock()
            ts.as_pandas.return_value = None
            return ts

        fetcher.client.time_series.side_effect = fake_time_series

        fetcher.fetch_batch_data(["XAU"], interval="1d", days=10)

        # The interval sent to TwelveData must be "1day", not "1d"
        assert captured.get("interval") == "1day", (
            f"Expected '1day' to be sent to API, got: {captured.get('interval')!r}"
        )

    def test_fetch_single_normalizes_interval(self, fetcher):
        """_fetch_single must also normalise interval."""
        captured = {}

        def fake_ts(**kwargs):
            captured.update(kwargs)
            ts = MagicMock()
            ts.as_pandas.return_value = _make_ohlcv()
            return ts

        fetcher.client.time_series.side_effect = fake_ts
        fetcher._fetch_single("XAU/USD", "1mo", 30)

        assert captured.get("interval") == "1month"


# ---------------------------------------------------------------------------
# 2. Symbol mapping
# ---------------------------------------------------------------------------

class TestSymbolMapping:
    """PRIMARY and FALLBACK symbol lookups."""

    @pytest.mark.parametrize("sym,expected", [
        ("XAU", "XAU/USD"),
        ("XAG", "XAG/USD"),
        ("WTI", "WTI/USD"),
        ("SPX", "SPX"),
        ("BTC", "BTC/USD"),
        ("DXY", "DXY"),        # fixed from DX-Y.NYB
        ("TNX", "TNX"),
        ("xau", "XAU/USD"),    # lowercase input
        ("UNKNOWN", "UNKNOWN"), # pass-through for unknown
    ])
    def test_primary_mapping(self, fetcher, sym, expected):
        assert fetcher.get_symbol_mapping(sym) == expected

    @pytest.mark.parametrize("sym,expected", [
        ("XAU", "GLD"),
        ("XAG", "SLV"),
        ("WTI", "USO"),
        ("BTC", "BITO"),
        ("SPX", "SPY"),
        ("DXY", "UUP"),        # fallback: ETF proxy for DXY
        ("TNX", None),          # no fallback defined
        ("UNKNOWN", None),
    ])
    def test_fallback_mapping(self, fetcher, sym, expected):
        assert fetcher.get_fallback_mapping(sym) == expected

    def test_dxy_is_not_dx_y_nyb(self, fetcher):
        """Regression: ensure the old invalid symbol is gone from all mappings."""
        all_mappings = {
            **fetcher.PRIMARY_MAPPINGS,
            **fetcher.FALLBACK_MAPPINGS,
        }
        assert "DX-Y.NYB" not in all_mappings.values(), (
            "DX-Y.NYB is an invalid TwelveData symbol and must not appear in mappings"
        )


# ---------------------------------------------------------------------------
# 3. fetch_batch_data — empty / None guards
# ---------------------------------------------------------------------------

class TestFetchBatchDataGuards:

    def test_empty_symbols_returns_empty_dict(self, fetcher):
        result = fetcher.fetch_batch_data([], interval="1day", days=30)
        assert result == {}

    def test_none_api_response_skips_symbol(self, fetcher):
        """If API returns None, the symbol must be absent — not crash."""
        ts = MagicMock()
        ts.as_pandas.return_value = None
        fetcher.client.time_series.return_value = ts

        result = fetcher.fetch_batch_data(["XAU"], interval="1day", days=30)
        assert "XAU" not in result

    def test_empty_dataframe_response_skips_symbol(self, fetcher):
        """If API returns empty DataFrame, symbol must be absent — not crash."""
        ts = MagicMock()
        ts.as_pandas.return_value = pd.DataFrame()
        fetcher.client.time_series.return_value = ts

        result = fetcher.fetch_batch_data(["XAU"], interval="1day", days=30)
        assert "XAU" not in result

    def test_api_exception_does_not_raise(self, fetcher):
        """A chunk-level API error must be caught; other symbols can still succeed."""
        fetcher.client.time_series.side_effect = Exception("TwelveData 429 Rate Limit")

        # Should not raise; should return empty dict (or partial)
        result = fetcher.fetch_batch_data(["XAU", "BTC"], interval="1day", days=10)
        assert isinstance(result, dict)

    def test_fallback_triggered_when_primary_missing(self, fetcher):
        """If primary fetch returns no data, fallback ETF must be attempted."""
        call_log = []

        def fake_ts(**kwargs):
            symbols_arg = kwargs.get("symbol", "")
            call_log.append(symbols_arg)
            ts = MagicMock()
            # First call (primary XAU/USD) → empty; second call (fallback GLD) → data
            if "XAU/USD" in symbols_arg:
                ts.as_pandas.return_value = pd.DataFrame()
            else:
                df = _make_ohlcv(100)
                ts.as_pandas.return_value = df
            return ts

        fetcher.client.time_series.side_effect = fake_ts

        result = fetcher.fetch_batch_data(["XAU"], interval="1day", days=30)
        # Fallback (GLD) should have been called
        assert any("GLD" in c for c in call_log), (
            f"Expected GLD fallback call. Calls were: {call_log}"
        )


# ---------------------------------------------------------------------------
# 4. _normalize_df — column resilience
# ---------------------------------------------------------------------------

class TestNormalizeDf:
    """_normalize_df should accept both lower and title-case column names."""

    def test_lowercase_columns(self, fetcher):
        df = _make_ohlcv(50)
        result = fetcher._normalize_df(df)
        assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(result.columns)

    def test_titlecase_columns_passthrough(self, fetcher):
        df = _make_ohlcv(50)
        df = df.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume", "datetime": "datetime"
        })
        result = fetcher._normalize_df(df)
        assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(result.columns)

    def test_missing_volume_gets_zero(self, fetcher):
        df = _make_ohlcv(50).drop(columns=["volume"])
        result = fetcher._normalize_df(df)
        assert "Volume" in result.columns
        assert (result["Volume"] == 0).all()


# ---------------------------------------------------------------------------
# 5. data_fetcher wrapper interval passthrough
# ---------------------------------------------------------------------------

class TestDataFetcherWrapper:

    def test_interval_1d_normalised_to_1day(self):
        """data_fetcher.fetch_historical_data('1d') → calls TwelveData with '1day'."""
        with patch("app.data_fetcher.get_td_fetcher") as mock_get:
            mock_td = MagicMock(spec=TwelveDataFetcher)
            mock_td._normalize_interval.side_effect = lambda x: TwelveDataFetcher._INTERVAL_ALIASES.get(x.lower(), x)
            mock_td.fetch_historical_data.return_value = _make_ohlcv()
            mock_get.return_value = mock_td
            mock_td.api_key = "FAKE"

            from app.data_fetcher import fetch_historical_data
            fetch_historical_data("XAU", days=30, interval="1d")

            call_interval = mock_td.fetch_historical_data.call_args[1].get("interval") or \
                            mock_td.fetch_historical_data.call_args[0][2]
            assert call_interval == "1day"

    def test_default_interval_is_1day(self):
        """Default interval must be '1day', not '1d'."""
        import inspect
        from app.data_fetcher import fetch_historical_data
        sig = inspect.signature(fetch_historical_data)
        default = sig.parameters["interval"].default
        assert default == "1day", f"Default interval should be '1day', got {default!r}"
