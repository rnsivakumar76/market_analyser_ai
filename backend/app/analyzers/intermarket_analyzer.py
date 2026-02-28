import pandas as pd
import logging
from typing import Optional
from ..models import IntermarketContext

logger = logging.getLogger(__name__)

# Symbols used for intermarket context
DXY_SYMBOL = 'DX-Y.NYB'   # TwelveData DXY equivalent; fallback to 'UUP'
US10Y_SYMBOL = 'TNX'       # 10-Year Treasury Yield Index

# Commodity symbols that are negatively correlated with DXY
COMMODITY_SYMBOLS = {'XAU', 'XAG', 'GLD', 'SLV', 'WTI', 'USO', 'OIL'}
CRYPTO_SYMBOLS = {'BTC', 'ETH', 'BITO', 'BTC/USD'}


def _slope_direction(series: pd.Series, lookback: int = 10) -> tuple[str, float]:
    """Return direction ('up','down','flat') and % change over lookback bars."""
    if len(series) < lookback + 1:
        return 'flat', 0.0
    old = float(series.iloc[-lookback])
    new = float(series.iloc[-1])
    if old == 0:
        return 'flat', 0.0
    pct = round((new - old) / old * 100, 2)
    if pct > 0.3:
        return 'up', pct
    elif pct < -0.3:
        return 'down', pct
    return 'flat', pct


def analyze_intermarket_context(
    symbol: str,
    dxy_df: Optional[pd.DataFrame],
    us10y_df: Optional[pd.DataFrame]
) -> Optional[IntermarketContext]:
    """
    Build intermarket context for a symbol.
    Currently meaningful for commodities (XAU, XAG, WTI) and crypto (BTC).
    
    Key correlations:
    - DXY UP  → Gold/Silver/Oil bearish (inverse correlation)
    - DXY DOWN → Gold/Silver/Oil bullish
    - US10Y UP → Gold bearish (opportunity cost of holding non-yielding asset)
    - US10Y DOWN → Gold bullish
    """
    sym = symbol.upper()
    is_commodity = any(c in sym for c in COMMODITY_SYMBOLS)
    is_crypto = any(c in sym for c in CRYPTO_SYMBOLS)

    if not (is_commodity or is_crypto):
        return None  # Only generate for relevant instruments

    try:
        dxy_dir, dxy_chg = _slope_direction(dxy_df['Close']) if dxy_df is not None and not dxy_df.empty else ('flat', 0.0)
        us10y_dir, us10y_chg = _slope_direction(us10y_df['Close']) if us10y_df is not None and not us10y_df.empty else ('flat', 0.0)

        # Determine implication for Gold (and similar safe-haven assets)
        bullish_factors = 0
        bearish_factors = 0

        if is_commodity:
            if dxy_dir == 'down':
                bullish_factors += 1
            elif dxy_dir == 'up':
                bearish_factors += 1

            if 'XAU' in sym or 'GLD' in sym or 'XAG' in sym or 'SLV' in sym:
                # Gold is especially sensitive to real yields via US10Y
                if us10y_dir == 'down':
                    bullish_factors += 1
                elif us10y_dir == 'up':
                    bearish_factors += 1

        if is_crypto:
            # BTC has become increasingly correlated with risk assets
            # DXY up = risk-off = bearish for crypto
            if dxy_dir == 'down':
                bullish_factors += 1
            elif dxy_dir == 'up':
                bearish_factors += 1

        if bullish_factors > bearish_factors:
            implication = 'bullish'
        elif bearish_factors > bullish_factors:
            implication = 'bearish'
        else:
            implication = 'neutral'

        # Build human-readable description
        parts = []
        if dxy_dir == 'up':
            parts.append(f"DXY rising ({dxy_chg:+.2f}%) → headwind for {sym}")
        elif dxy_dir == 'down':
            parts.append(f"DXY falling ({dxy_chg:+.2f}%) → tailwind for {sym}")
        else:
            parts.append(f"DXY flat ({dxy_chg:+.2f}%)")

        if us10y_dir == 'up':
            parts.append(f"10Y yield rising ({us10y_chg:+.2f}%) → pressure on {sym}")
        elif us10y_dir == 'down':
            parts.append(f"10Y yield falling ({us10y_chg:+.2f}%) → supportive for {sym}")
        else:
            parts.append(f"10Y yield flat ({us10y_chg:+.2f}%)")

        return IntermarketContext(
            dxy_direction=dxy_dir,
            dxy_change_pct=dxy_chg,
            us10y_direction=us10y_dir,
            us10y_change_pct=us10y_chg,
            gold_implication=implication,
            description='. '.join(parts) + '.'
        )

    except Exception as e:
        logger.warning(f"Intermarket context failed for {symbol}: {e}")
        return None
