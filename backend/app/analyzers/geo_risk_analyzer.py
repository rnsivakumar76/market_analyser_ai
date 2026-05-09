"""
Geopolitical Risk Analyzer
Detects geopolitical events from news headlines and cross-validates with
technical indicators (ATR, ADX, Volume, RSI) to determine whether the
market is CONFIRMING, DIVERGING, or has an EARLY reaction to the event.
"""
from typing import List, Dict, Tuple


# ── Keyword taxonomy ──────────────────────────────────────────────────────────
_GEO_KEYWORDS: Dict[str, List[str]] = {
    'conflict': [
        'war', 'airstrike', 'air strike', 'missile', 'attack', 'invasion',
        'troops', 'military', 'bombing', 'escalation', 'combat',
        'drone strike', 'nuclear threat', 'shelling', 'explosion',
    ],
    'middle_east': [
        'iran', 'israel', 'gaza', 'hezbollah', 'hamas', 'lebanon',
        'strait of hormuz', 'yemen', 'houthi', 'saudi arabia', 'opec',
        'iraq', 'syria', 'red sea', 'suez canal', 'persian gulf',
    ],
    'sanctions': [
        'sanctions', 'embargo', 'ban', 'blacklist', 'freeze',
        'asset seizure', 'trade war', 'tariff', 'restrictions',
        'export controls',
    ],
    'supply_shock': [
        'oil supply', 'pipeline', 'refinery', 'production cut', 'opec+',
        'output cut', 'energy crisis', 'shortage', 'disruption',
        'crude output', 'supply cut',
    ],
    'safe_haven': [
        'safe haven', 'risk off', 'flight to safety', 'flight to quality',
        'vix', 'fear index', 'panic', 'crisis', 'sell-off', 'uncertainty',
    ],
    'deescalation': [
        'ceasefire', 'peace deal', 'negotiations', 'de-escalation',
        'truce', 'agreement', 'diplomacy', 'resolve', 'calm', 'talks',
    ],
}

# ── Per-instrument impact mapping ─────────────────────────────────────────────
# (symbol_group, event_category) -> (expected_direction, impact_confidence)
_IMPACT_MAP: Dict[Tuple[str, str], Tuple[str, str]] = {
    # Crude Oil / WTI
    ('crude', 'conflict'):       ('bullish', 'HIGH'),
    ('crude', 'middle_east'):    ('bullish', 'HIGH'),
    ('crude', 'sanctions'):      ('bullish', 'MEDIUM'),
    ('crude', 'supply_shock'):   ('bullish', 'HIGH'),
    ('crude', 'safe_haven'):     ('bullish', 'LOW'),
    ('crude', 'deescalation'):   ('bearish', 'HIGH'),

    # Gold / Silver
    ('gold', 'conflict'):        ('bullish', 'HIGH'),
    ('gold', 'middle_east'):     ('bullish', 'HIGH'),
    ('gold', 'sanctions'):       ('bullish', 'MEDIUM'),
    ('gold', 'supply_shock'):    ('bullish', 'LOW'),
    ('gold', 'safe_haven'):      ('bullish', 'HIGH'),
    ('gold', 'deescalation'):    ('bearish', 'HIGH'),

    # Bitcoin / Crypto
    ('crypto', 'conflict'):      ('bullish', 'MEDIUM'),
    ('crypto', 'middle_east'):   ('bullish', 'MEDIUM'),
    ('crypto', 'sanctions'):     ('bullish', 'HIGH'),
    ('crypto', 'supply_shock'):  ('neutral', 'LOW'),
    ('crypto', 'safe_haven'):    ('bullish', 'MEDIUM'),
    ('crypto', 'deescalation'):  ('neutral', 'LOW'),

    # Equities / Indices
    ('equity', 'conflict'):      ('bearish', 'HIGH'),
    ('equity', 'middle_east'):   ('bearish', 'MEDIUM'),
    ('equity', 'sanctions'):     ('bearish', 'MEDIUM'),
    ('equity', 'supply_shock'):  ('bearish', 'HIGH'),
    ('equity', 'safe_haven'):    ('bearish', 'HIGH'),
    ('equity', 'deescalation'):  ('bullish', 'HIGH'),

    # Forex (USD pairs / DXY)
    ('forex', 'conflict'):       ('usd_bullish', 'MEDIUM'),
    ('forex', 'middle_east'):    ('usd_bullish', 'MEDIUM'),
    ('forex', 'sanctions'):      ('usd_bullish', 'HIGH'),
    ('forex', 'supply_shock'):   ('mixed', 'LOW'),
    ('forex', 'safe_haven'):     ('usd_bullish', 'MEDIUM'),
    ('forex', 'deescalation'):   ('usd_bearish', 'MEDIUM'),
}


def _get_symbol_group(symbol: str) -> str:
    s = symbol.upper()
    if any(x in s for x in ['WTI', 'CL', 'OIL', 'BRENT', 'USOIL']): return 'crude'
    if any(x in s for x in ['XAU', 'GOLD', 'XAG', 'SILVER']):         return 'gold'
    if any(x in s for x in ['BTC', 'ETH', 'CRYPTO', 'COIN']):          return 'crypto'
    if any(x in s for x in ['SPX', 'NAS', 'DOW', 'SPY', 'QQQ', 'NDX']): return 'equity'
    if any(x in s for x in ['EUR', 'GBP', 'JPY', 'DXY', 'USD']):       return 'forex'
    return 'equity'


def _scan_keywords(news_items) -> Dict[str, List[str]]:
    """Return {category: [matched_keywords]} from headline text."""
    all_text = ' '.join(item.title.lower() for item in news_items)
    result: Dict[str, List[str]] = {}
    for category, keywords in _GEO_KEYWORDS.items():
        found = [kw for kw in keywords if kw in all_text]
        if found:
            result[category] = found
    return result


def _indicator_checks(
    adx: float,
    rsi: float,
    volume_ratio: float,
    atr_percentile: float,
    expected_direction: str,
    trade_direction: str,
) -> list:
    from ..models import GeoIndicatorCheck
    checks = []

    # 1. ATR / Volatility
    if atr_percentile >= 70:
        status, desc = 'confirming', (
            f"ATR at {atr_percentile:.0f}th pct — elevated volatility confirms geo-driven price reaction"
        )
    elif atr_percentile >= 45:
        status, desc = 'neutral', (
            f"ATR at {atr_percentile:.0f}th pct — moderate volatility, early geo reaction possible"
        )
    else:
        status, desc = 'diverging', (
            f"ATR at {atr_percentile:.0f}th pct — normal volatility, geo news not yet moving price"
        )
    checks.append(GeoIndicatorCheck(name='ATR / Volatility', value=round(atr_percentile, 1),
                                    status=status, description=desc))

    # 2. ADX / Trend Strength
    bullish_expected = expected_direction in ('bullish', 'usd_bullish')
    bearish_expected = expected_direction in ('bearish', 'usd_bearish')
    if adx >= 30:
        dir_match = (bullish_expected and trade_direction == 'bullish') or \
                    (bearish_expected and trade_direction == 'bearish')
        if dir_match:
            status, desc = 'confirming', (
                f"ADX={adx:.1f} — strong trend aligned with geo impact direction"
            )
        else:
            status, desc = 'diverging', (
                f"ADX={adx:.1f} — strong trend but direction opposes expected geo impact"
            )
    elif adx >= 20:
        status, desc = 'neutral', (f"ADX={adx:.1f} — developing trend, geo momentum building")
    else:
        status, desc = 'diverging', (f"ADX={adx:.1f} — weak trend, geo news not yet directional")
    checks.append(GeoIndicatorCheck(name='ADX / Trend Strength', value=round(adx, 1),
                                    status=status, description=desc))

    # 3. Volume Ratio
    if volume_ratio >= 1.8:
        status, desc = 'confirming', (
            f"Volume {volume_ratio:.1f}x avg — institutional flows active (smart money reacting)"
        )
    elif volume_ratio >= 1.3:
        status, desc = 'neutral', (
            f"Volume {volume_ratio:.1f}x avg — above-normal interest, watching for surge"
        )
    elif volume_ratio >= 0.8:
        status, desc = 'neutral', (
            f"Volume {volume_ratio:.1f}x avg — normal participation, geo risk not yet moving the needle"
        )
    else:
        status, desc = 'diverging', (
            f"Volume {volume_ratio:.1f}x avg — below-average conviction, geo risk not driving flows"
        )
    checks.append(GeoIndicatorCheck(name='Volume Ratio', value=round(volume_ratio, 2),
                                    status=status, description=desc))

    # 4. RSI Momentum
    if bullish_expected:
        if rsi >= 55:
            status, desc = 'confirming', (f"RSI={rsi:.1f} — bullish momentum confirms geo impact bias")
        elif rsi >= 45:
            status, desc = 'neutral', (f"RSI={rsi:.1f} — neutral, watching for geo-driven breakout above 55")
        else:
            status, desc = 'diverging', (f"RSI={rsi:.1f} — bearish momentum contradicts bullish geo expectation")
    elif bearish_expected:
        if rsi <= 45:
            status, desc = 'confirming', (f"RSI={rsi:.1f} — bearish momentum confirms geo impact bias")
        elif rsi <= 55:
            status, desc = 'neutral', (f"RSI={rsi:.1f} — neutral, watching for geo-driven break below 45")
        else:
            status, desc = 'diverging', (f"RSI={rsi:.1f} — bullish momentum contradicts bearish geo expectation")
    else:
        status, desc = 'neutral', (f"RSI={rsi:.1f} — mixed/neutral geo impact expected for this instrument")
    checks.append(GeoIndicatorCheck(name='RSI / Momentum', value=round(rsi, 1),
                                    status=status, description=desc))

    return checks


def _narrative(
    symbol: str,
    event_categories: List[str],
    keywords_found: List[str],
    expected_direction: str,
    impact_confidence: str,
    confirmation: str,
    risk_score: int,
    confirming_count: int,
    adx: float,
    rsi: float,
    vol_ratio: float,
    atr_pct: float,
    top_headlines: List[str],
) -> str:
    """
    Build a contextual narrative that incorporates real indicator values,
    specific keywords, and actual news headline snippets.
    """
    import random

    # ── Event description ─────────────────────────────────────────────────────
    if 'middle_east' in event_categories and 'conflict' in event_categories:
        event_desc = "Middle East conflict / military escalation"
    elif 'middle_east' in event_categories:
        event_desc = "Middle East geopolitical tension"
    elif 'conflict' in event_categories:
        event_desc = "armed conflict / military escalation"
    elif 'deescalation' in event_categories:
        event_desc = "geopolitical de-escalation / diplomatic progress"
    elif 'sanctions' in event_categories:
        event_desc = "sanctions / trade restrictions"
    elif 'supply_shock' in event_categories:
        event_desc = "energy supply disruption"
    elif 'safe_haven' in event_categories:
        event_desc = "risk-off / safe-haven demand"
    else:
        event_desc = "geopolitical risk"

    dir_label = {
        'bullish': 'bullish', 'bearish': 'bearish',
        'usd_bullish': 'USD-strengthening', 'usd_bearish': 'USD-weakening', 'mixed': 'mixed'
    }.get(expected_direction, 'neutral')

    # ── Instrument-specific context sentence ──────────────────────────────────
    sg = _get_symbol_group(symbol)
    if sg == 'crude' and expected_direction == 'bullish':
        _route_kws = [k for k in keywords_found if k in ['strait of hormuz', 'red sea', 'suez canal', 'pipeline', 'opec+']]
        _routes = '\u2019, '.join(_route_kws) if _route_kws else 'key shipping routes'
        instrument_ctx = (
            f"Supply disruption risk via {_routes} "
            f"typically adds a $2\u20136/bbl geopolitical premium to WTI."
        )
    elif sg == 'gold' and expected_direction == 'bullish':
        instrument_ctx = (
            f"Gold historically outperforms during {event_desc} events, "
            f"with safe-haven flows and USD debasement concerns amplifying the move."
        )
    elif sg == 'crypto' and expected_direction == 'bullish':
        instrument_ctx = (
            f"Crypto often attracts capital flight from sanctioned or conflict-affected economies, "
            f"acting as a borderless store of value."
        )
    elif expected_direction == 'bearish':
        instrument_ctx = (
            f"Risk assets like {symbol} typically face selling pressure as capital rotates to safe havens."
        )
    else:
        instrument_ctx = ""

    # ── Headline snippet (first matching title, truncated) ────────────────────
    headline_str = ""
    if top_headlines:
        hl = top_headlines[0][:110]
        if len(top_headlines[0]) > 110:
            hl += "\u2026"
        headline_str = f' Headlines driving this: \u201c{hl}\u201d'
        if len(top_headlines) > 1:
            hl2 = top_headlines[1][:80]
            if len(top_headlines[1]) > 80:
                hl2 += "\u2026"
            headline_str += f' and \u201c{hl2}\u201d.'
        else:
            headline_str += "."

    # ── Specific keywords context ─────────────────────────────────────────────
    hot_kw = [k for k in keywords_found if k in {
        'iran', 'israel', 'houthi', 'red sea', 'strait of hormuz', 'suez canal',
        'opec', 'opec+', 'pipeline', 'airstrike', 'missile', 'ceasefire',
        'sanctions', 'russia', 'taiwan', 'nuclear threat',
    }]
    kw_str = ""
    if hot_kw:
        kw_str = f" Key signals: {', '.join(hot_kw[:4])}."

    # ── Indicator summary ─────────────────────────────────────────────────────
    ind_parts = []
    if atr_pct >= 70:
        ind_parts.append(f"ATR at {atr_pct:.0f}th pct (elevated volatility)")
    elif atr_pct >= 45:
        ind_parts.append(f"ATR at {atr_pct:.0f}th pct (building volatility)")
    else:
        ind_parts.append(f"ATR at {atr_pct:.0f}th pct (subdued volatility)")

    if adx >= 30:
        ind_parts.append(f"ADX {adx:.1f} (strong trend)")
    elif adx >= 20:
        ind_parts.append(f"ADX {adx:.1f} (developing trend)")
    else:
        ind_parts.append(f"ADX {adx:.1f} (no clear trend yet)")

    if vol_ratio >= 1.8:
        ind_parts.append(f"volume {vol_ratio:.1f}\u00d7 avg (institutional activity)")
    elif vol_ratio >= 1.3:
        ind_parts.append(f"volume {vol_ratio:.1f}\u00d7 avg (above normal)")
    else:
        ind_parts.append(f"volume {vol_ratio:.1f}\u00d7 avg (light)")

    ind_parts.append(f"RSI {rsi:.1f}")
    ind_summary = "; ".join(ind_parts)

    # ── State-specific narrative assembly ────────────────────────────────────
    if confirmation == 'CONFIRMED':
        openers = [
            f"{event_desc.capitalize()} is confirmed as a live market driver for {symbol}.",
            f"Price action on {symbol} is aligning with the unfolding {event_desc}.",
            f"Technical indicators are now validating the {event_desc} narrative on {symbol}.",
        ]
        body = (
            f"{confirming_count}/4 indicators confirm geo momentum [{ind_summary}]."
            f"{headline_str}{kw_str}"
            f" {impact_confidence} confidence {dir_label} bias. {instrument_ctx}"
            f" Geo-driven moves can reverse sharply on ceasefire or diplomacy news — manage position size accordingly."
        )
        return f"{random.choice(openers)} {body}"

    elif confirmation == 'DIVERGING':
        openers = [
            f"{event_desc.capitalize()} headlines are active, but {symbol} price action is NOT confirming.",
            f"Market is discounting the {event_desc} news — {symbol} indicators diverge from expected impact.",
            f"Despite active {event_desc} signals, {symbol} is not reacting as expected.",
        ]
        body = (
            f"Only {confirming_count}/4 indicators show geo-driven momentum [{ind_summary}]."
            f"{headline_str}{kw_str}"
            f" Possible explanations: market has already priced in the risk, a diplomatic counter-narrative"
            f" is active, or the reaction is delayed. Wait for volume ({'>'}1.5\u00d7) and ATR ({'>'}70th pct)"
            f" to confirm before entering. False breakout risk is elevated."
        )
        return f"{random.choice(openers)} {body}"

    elif confirmation == 'EARLY':
        openers = [
            f"Early-stage {event_desc} signals are emerging for {symbol}.",
            f"{event_desc.capitalize()} risk is building — {symbol} showing initial geo reaction.",
            f"Geo radar is lit: early {event_desc} indicators detected for {symbol}.",
        ]
        body = (
            f"{confirming_count}/4 indicators beginning to confirm [{ind_summary}]."
            f"{headline_str}{kw_str}"
            f" Expected {dir_label} impact ({impact_confidence} confidence). {instrument_ctx}"
            f" Watch for ATR break above 70th pct and volume surge {'>'}1.5\u00d7 as primary triggers."
            f" Second-wave reactions typically materialise within 24\u201348h of initial escalation."
        )
        return f"{random.choice(openers)} {body}"

    else:  # NONE
        openers = [
            f"Geopolitical keywords detected in {symbol} headlines, but market impact is not yet visible.",
            f"Background {event_desc} noise present — no material price reaction confirmed yet for {symbol}.",
        ]
        body = (
            f"Risk score: {risk_score}/100 [{ind_summary}]."
            f"{headline_str}{kw_str}"
            f" Indicators show normal conditions. Monitor news flow — a sudden escalation could shift"
            f" this picture rapidly. Set alerts on ATR and volume for early warning."
        )
        return f"{random.choice(openers)} {body}"


def analyze_geopolitical_risk(symbol: str, news_sentiment, strength, volatility, trade_signal):
    """
    Main entry point. Returns a GeopoliticalRisk model.
    Args:
        symbol:         Instrument symbol (e.g. 'XAU', 'WTI', 'BTC')
        news_sentiment: NewsSentiment model (may be None)
        strength:       StrengthAnalysis model (adx, rsi, volume_ratio)
        volatility:     VolatilityAnalysis model (atr, atr_percentile_rank)
        trade_signal:   TradeSignal model (recommendation)
    """
    from ..models import GeopoliticalRisk

    _empty = lambda msg: GeopoliticalRisk(
        detected=False, risk_score=0, risk_level='NONE',
        keywords_found=[], event_categories=[],
        expected_impact='neutral', impact_confidence='LOW',
        indicator_confirmation='NONE', indicators=[],
        ai_narrative=msg, action_bias='MONITOR NEWS'
    )

    if not news_sentiment or not news_sentiment.news_items:
        return _empty('No news available to assess geopolitical risk.')

    matches = _scan_keywords(news_sentiment.news_items)
    if not matches:
        return _empty('No geopolitical keywords detected in recent headlines.')

    # Flatten unique keywords (cap at 8 for display)
    all_kw = list({kw for kws in matches.values() for kw in kws})[:8]
    cats = list(matches.keys())

    # Keyword score: each category = 20 pts, cap at 80
    kw_score = min(len(cats) * 20, 80)

    # Expected direction
    sg = _get_symbol_group(symbol)
    expected_dir, impact_conf = 'neutral', 'LOW'
    for cat in ['middle_east', 'conflict', 'supply_shock', 'sanctions', 'safe_haven', 'deescalation']:
        if cat in cats and (sg, cat) in _IMPACT_MAP:
            expected_dir, impact_conf = _IMPACT_MAP[(sg, cat)]
            break

    # Indicator values
    adx            = float(getattr(strength,   'adx',               20.0) or 20.0)
    rsi            = float(getattr(strength,   'rsi',               50.0) or 50.0)
    vol_ratio      = float(getattr(strength,   'volume_ratio',       1.0) or 1.0)
    atr_pct        = float(getattr(volatility, 'atr_percentile_rank', 50.0) or 50.0)
    trade_dir      = str(getattr(getattr(trade_signal, 'recommendation', None), 'value', 'neutral'))

    indicators = _indicator_checks(adx, rsi, vol_ratio, atr_pct, expected_dir, trade_dir)

    confirming = sum(1 for i in indicators if i.status == 'confirming')
    diverging  = sum(1 for i in indicators if i.status == 'diverging')
    ind_boost  = confirming * 5
    total      = min(kw_score + ind_boost, 100)

    # Risk level
    if total >= 80:   risk_level = 'CRITICAL'
    elif total >= 60: risk_level = 'HIGH'
    elif total >= 40: risk_level = 'MODERATE'
    elif total >= 20: risk_level = 'LOW'
    else:             risk_level = 'NONE'

    # Confirmation
    if total < 20:
        confirmation = 'NONE'
    elif confirming >= 3:
        confirmation = 'CONFIRMED'
    elif confirming >= 2:
        confirmation = 'EARLY'
    elif diverging >= 3:
        confirmation = 'DIVERGING'
    else:
        confirmation = 'EARLY'

    # Action bias
    bias_map = {
        ('CONFIRMED',  'bullish'):     'TRADE WITH GEO MOMENTUM',
        ('CONFIRMED',  'usd_bullish'): 'TRADE WITH GEO MOMENTUM',
        ('CONFIRMED',  'bearish'):     'REDUCE LONG EXPOSURE',
        ('CONFIRMED',  'usd_bearish'): 'REDUCE LONG EXPOSURE',
        ('EARLY',      'bullish'):     'WAIT FOR CONFIRMATION',
        ('EARLY',      'usd_bullish'): 'WAIT FOR CONFIRMATION',
        ('EARLY',      'bearish'):     'WAIT FOR CONFIRMATION',
        ('DIVERGING',  'bullish'):     'WAIT — NEWS NOT PRICED IN YET',
        ('DIVERGING',  'bearish'):     'WAIT — NEWS NOT PRICED IN YET',
    }
    action_bias = bias_map.get((confirmation, expected_dir), 'MONITOR NEWS')

    # Collect headlines that contain at least one matched keyword (top 2 for narrative)
    _all_kw_set = {kw for kws in matches.values() for kw in kws}
    top_headlines = [
        item.title for item in news_sentiment.news_items
        if any(kw in item.title.lower() for kw in _all_kw_set)
    ][:2]

    ai_text = _narrative(
        symbol, cats, all_kw, expected_dir, impact_conf,
        confirmation, total, confirming,
        adx, rsi, vol_ratio, atr_pct, top_headlines,
    )

    return GeopoliticalRisk(
        detected=True,
        risk_score=total,
        risk_level=risk_level,
        keywords_found=all_kw,
        event_categories=cats,
        expected_impact=expected_dir,
        impact_confidence=impact_conf,
        indicator_confirmation=confirmation,
        indicators=indicators,
        ai_narrative=ai_text,
        action_bias=action_bias,
    )
