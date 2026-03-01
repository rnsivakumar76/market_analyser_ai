# WIREFRAMES & DESIGN — GUI 3.0 (Institutional Features)
**Status:** CONFIRMED — Implementation in progress  
**Branch:** `gui3.0`  
**Previous version:** v3.0 (tag) on `main`

---

## Feasibility Matrix

| Feature | Feasible? | Data Source | Effort |
|---|---|---|---|
| Volume Profile (POC/VAH/VAL) | ✅ Partial | TwelveData OHLCV bins | Medium |
| Conflicting Signal Resolution | ✅ Full | Existing signal_generator.py | Low |
| Liquidity Map | ✅ Approximate | Swing highs/lows from OHLCV | Medium |
| Session VWAP (London/NY/Asia) | ✅ Full | TwelveData 1h intraday | Medium |
| Dark Pool / Block Alerts | ⚠️ Approximate | Volume spike detection only | Low |
| Economic Calendar Pre-event Trigger | ✅ Full | Extend existing fundamentals | Low |
| Live Correlation Coefficients | ✅ Full | Already calculated, just expose | Low |
| MAE (Max Adverse Excursion) | ✅ Full | Extend backtest_engine.py | Low |
| Volatility Regime (ATR %ile Rank) | ✅ Full | Extend volatility_analyzer.py | Low |

**Not feasible with current stack (TwelveData):**
- True dark pool prints (requires Unusual Whales / CBOE feeds)
- Options data / GEX (requires options chain feed)
- Level 2 / order book depth

---

## Architecture Changes

### New Backend Files
- `backend/app/analyzers/volume_profile_analyzer.py` — POC/VAH/VAL from daily OHLCV bins
- `backend/app/analyzers/liquidity_analyzer.py` — stop cluster levels from swing highs/lows
- `backend/app/analyzers/session_vwap_analyzer.py` — Asia/London/NY anchored VWAPs from 1h data

### Extended Backend Files
- `signal_generator.py` — conflicting signal resolution logic (ADX vs direction)
- `volatility_analyzer.py` — add ATR percentile rank + HV (historical volatility)
- `backtest_engine.py` — add MAE, sample size, Sharpe ratio, max drawdown, streak
- `correlation_analyzer.py` — expose per-instrument coefficients vs DXY/SPX/BTC benchmarks
- `fundamentals_analyzer.py` — add event timestamps + pre-event risk reduction flag
- `models.py` — new/extended Pydantic models for all the above

### New Frontend Sections
- Technical tab: Volume Profile visual + Session VWAP display
- Technical tab: Signal Conflict Resolution banner
- Risk tab: Liquidity Map display
- Risk tab: Backtest Quality block (MAE, Sharpe, drawdown)
- Context Panel: Correlation coefficients row
- Context Panel: Pre-event risk reduction alert banner

---

## Section 1 — Conflicting Signal Resolution (PRIORITY 1)

**Location:** Technical tab — above Strategic Action & Scaling  
**Backend change:** `signal_generator.py`

### Logic
When `ADX >= 35` (strong trend) but `direction == NEUTRAL` or mixed MTF signals:
- Current: "Wait and Observe" — misleading, implies no trend
- New: Specific conflict badge + explanation

### New `signal_conflict` field in `TradeSignal` model
```
signal_conflict: Optional[SignalConflict]
  type: "adx_direction_mismatch" | "mtf_disagreement" | "none"
  severity: "high" | "medium" | "none"
  headline: str   e.g. "ADX=38 confirms LOCKED TREND — but Monthly direction is NEUTRAL"
  guidance: str   e.g. "Wait for breakout above $68,900 (R1) to confirm bullish or below $64,071 (S1) to confirm bearish"
  trigger_price_up: float
  trigger_price_down: float
```

### UI Wireframe
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ SIGNAL CONFLICT DETECTED                            HIGH      │
│                                                                   │
│  ADX=38 confirms LOCKED TREND but Monthly bias is NEUTRAL        │
│  Strong momentum exists — but direction is unconfirmed.          │
│                                                                   │
│  WATCH: Break above $68,900 → BULLISH TRIGGER                    │
│         Break below $64,071 → BEARISH TRIGGER                    │
│                                                                   │
│  Recommended: Wait for breakout confirmation before entry.        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 2 — ATR Percentile Rank + Volatility Regime (PRIORITY 2)

**Location:** Technical tab — Technical Heat section  
**Backend change:** `volatility_analyzer.py`

### New fields in `VolatilityAnalysis`
```
atr_percentile_rank: float     # 0-100, e.g. 72.4
atr_regime: str                # "LOW" | "NORMAL" | "ELEVATED" | "EXTREME"
historical_volatility_14: float  # 14-day HV (annualized)
hv_percentile: float           # Historical volatility percentile rank
volatility_regime_label: str   # "Compressed" | "Normal" | "Expanding" | "Extreme"
```

### ATR Percentile Rank Calculation
```python
# Compare current ATR to trailing 252-day (1 year) ATR values
atr_series = rolling 14-day ATR over full history
atr_percentile_rank = percentileofscore(atr_series, current_atr)
```

### Regime Classification
| ATR %ile | HV %ile | Label | Color |
|---|---|---|---|
| 0–25 | 0–25 | Compressed | Blue |
| 25–60 | 25–60 | Normal | Green |
| 60–80 | 60–80 | Expanding | Amber |
| 80–100 | 80–100 | Extreme | Red |

### UI Wireframe (replaces vague "MODERATE")
```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 TECHNICAL HEAT                                                │
│                                                                   │
│  ADX Strength     ████████░░░░░░░░  STRONG TREND                 │
│  RSI Power               ●          NEUTRAL                      │
│                                                                   │
│  VOLATILITY REGIME                                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ATR Percentile   72nd %ile  [████████████████░░░░]         │  │
│  │ HV (14-day)      28.4%      65th %ile                      │  │
│  │ Regime           EXPANDING          ← was "MODERATE"        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Trade Impact:   HIGH                                            │
│  Recommendation: Trend Following                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 3 — Volume Profile (POC / VAH / VAL) (PRIORITY 3)

**Location:** Technical tab — new block after Pivot Matrix  
**Backend change:** new `volume_profile_analyzer.py`

### Approximation Method (no Level 2 needed)
```
1. Take 30 days of daily OHLCV bars
2. Divide price range into N buckets (default N=20)
3. Distribute each bar's volume across the intrabar price range (uniform assumption)
4. Sum volume per bucket → volume histogram
5. POC = bucket with highest volume
6. Total value area = 70% of total volume
7. VAH/VAL = upper/lower bounds containing 70% from POC outward
```

### Notes on data availability
- BTC, XAU, XAG — volume data ✅
- SPX, DXY — volume = 0 from TwelveData → fall back to tick-count proxy

### New `VolumeProfile` model
```
poc: float          # Point of Control price
vah: float          # Value Area High
val: float          # Value Area Low
value_area_pct: float  # e.g. 70.0
price_vs_va: str    # "ABOVE_VA" | "IN_VA" | "BELOW_VA"
price_vs_poc: str   # "ABOVE_POC" | "AT_POC" | "BELOW_POC"
histogram: List[{price: float, volume: float, is_poc: bool}]  # for chart rendering
description: str
```

### UI Wireframe
```
┌─────────────────────────────────────────────────────────────────┐
│ 📦 VOLUME PROFILE (30-Day)                                       │
│                                                                   │
│  $76,200  ░░░                                                     │
│  $75,853  ░░░░░                  ← VAH                           │
│  $74,100  ░░░░░░░░                                               │
│  $72,400  ░░░░░░░░░░░░░░░        ← POC  (highest volume)         │
│  $70,800  ░░░░░░░░░░░                                             │
│  $69,200  ░░░░░░░                ← Current Price ●               │
│  $67,500  ░░░░░                  ← VAL                           │
│  $65,000  ░░                                                     │
│                                                                   │
│  POC: $72,400   VAH: $75,853   VAL: $67,500                      │
│  Price is BELOW VALUE AREA — selling pressure dominant           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 4 — Session VWAP (London / NY / Asia) (PRIORITY 4)

**Location:** Technical tab — Strategic Action & Scaling section (below entry levels)  
**Backend change:** new `session_vwap_analyzer.py` + new 1h intraday fetch

### Session Windows (UTC)
| Session | Start UTC | End UTC |
|---|---|---|
| Asia | 00:00 | 08:59 |
| London | 07:00 | 16:59 |
| New York | 13:00 | 21:59 |
| Current Open | First bar of today | Now |

### Calculation
```python
# Fetch 1h bars for last 5 days
# For each session: VWAP = sum(typical_price * volume) / sum(volume)
# typical_price = (H + L + C) / 3
session_vwap = sum(tp * vol) / sum(vol) for bars within session window
```

### Lambda constraint — minimize extra API calls
- Fetch `1h` intraday data in the SAME batch call as daily data (add to `fetch_batch_data` parallel thread)
- Cache intraday data separately (10-min TTL)

### New `SessionVWAP` model
```
asia_vwap: Optional[float]
london_vwap: Optional[float]
ny_vwap: Optional[float]
current_session: str    # "ASIA" | "LONDON" | "NEW_YORK" | "OFF_HOURS"
price_vs_asia_vwap: str   # "ABOVE" | "BELOW" | "AT"
price_vs_london_vwap: str
price_vs_ny_vwap: str
```

### UI Wireframe (added to levels display in Section 1)
```
  ENTRY ZONE          STOP               TARGET
  $64,071–74,502    $63,376            $75,854

  SESSION VWAPs
  ┌────────────┬────────────┬────────────┐
  │ ASIA VWAP  │ LON VWAP   │ NY VWAP    │
  │ $67,240    │ $68,890    │ —          │
  │ ▼ BELOW    │ ▼ BELOW    │ CLOSED     │
  └────────────┴────────────┴────────────┘
  Active Session: LONDON
```

---

## Section 5 — Liquidity Map (PRIORITY 5)

**Location:** Risk tab — new card between the two existing cards  
**Backend change:** new `liquidity_analyzer.py`

### Approximation Method
```
Buy-side liquidity (sell stops above price):
  - Swing highs from last 20 bars (local peaks)
  - Round numbers above price (e.g. $70,000, $75,000, $80,000)
  - Previous all-time high / week high

Sell-side liquidity (buy stops below price):
  - Swing lows from last 20 bars
  - Round numbers below price
  - Previous week low / month low

Strength rating per level = recency + how many times price touched without breaking
```

### New `LiquidityMap` model
```
buy_side_levels: List[{price: float, label: str, strength: "HIGH"|"MEDIUM"|"LOW", distance_pct: float}]
sell_side_levels: List[{price: float, label: str, strength: "HIGH"|"MEDIUM"|"LOW", distance_pct: float}]
nearest_buy_side: float
nearest_sell_side: float
description: str
```

### UI Wireframe
```
┌─────────────────────────────────────────────────────────────────┐
│ 💧 LIQUIDITY MAP                                                 │
│                                                                   │
│  BUY-SIDE LIQUIDITY (Stop Hunts Above)                           │
│  ●●● $75,853  Previous Weekly High     +11.9%  HIGH             │
│  ●●○ $72,000  Round Number             +6.5%   MEDIUM           │
│  ●○○ $69,500  Swing High (3 days ago)  +2.7%   LOW              │
│                                                                   │
│  ── CURRENT PRICE: $67,535 ──────────────────────────────────── │
│                                                                   │
│  SELL-SIDE LIQUIDITY (Stop Hunts Below)                          │
│  ●●○ $65,000  Round Number             -3.8%   MEDIUM           │
│  ●●● $63,376  Weekly Low / Stop Zone   -6.2%   HIGH             │
│  ●○○ $60,000  Round Number             -11.2%  LOW              │
│                                                                   │
│  NEAREST HUNT: $69,500 (+2.7%) then $65,000 (-3.8%)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 6 — Live Correlation Coefficients (PRIORITY 6)

**Location:** Risk tab Validation card — replaces "ANALYZING" placeholder  
**Backend change:** `correlation_analyzer.py` — expose per-instrument vs benchmarks

### Current state
- `correlation_analyzer.py` already calculates full Pearson matrix
- It's returned as a modal-only dataset, not per-instrument

### Change
- In `main.py`, after correlations are calculated, extract per-instrument
  coefficients against DXY, SPX, BTC (the three benchmarks)
- Add `instrument_correlations` to each `InstrumentAnalysis`

### New `InstrumentCorrelations` model
```
vs_dxy: Optional[float]      # e.g. -0.82
vs_spx: Optional[float]      # e.g. +0.71
vs_btc: Optional[float]      # e.g. +0.94 (for altcoins)
period_days: int             # e.g. 30
interpretation: str          # "Strong negative DXY correlation — risk asset"
```

### UI Wireframe (replaces "ANALYZING" in Risk Validation card)
```
  MARKET CORRELATION
  ┌──────────┬──────────┬──────────┐
  │ vs DXY   │ vs SPX   │ vs BTC   │
  │  -0.82   │  +0.71   │  +0.94   │
  │  STRONG↓ │  STRONG↑ │  STRONG↑ │
  └──────────┴──────────┴──────────┘
  Risk asset. Moves inversely with DXY.
```

---

## Section 7 — MAE + Backtest Quality (PRIORITY 7)

**Location:** Risk tab — below Probability/Backtest row  
**Backend change:** `backtest_engine.py` + `models.py`

### New fields in `BacktestAnalysis`
```
sharpe_ratio: float           # e.g. 1.84
max_drawdown_pct: float       # e.g. -18.4
max_consecutive_losses: int   # e.g. 4
max_adverse_excursion_pct: float  # e.g. 2.8 (avg MAE on winning trades before hitting target)
sample_size: int              # How many trades the backtest covers
expectancy: float             # (win_rate * avg_win) - (loss_rate * avg_loss)
```

### MAE Calculation
```python
# For each winning trade in backtest:
#   MAE = max adverse move (lowest close - entry) / entry * 100 (for longs)
#   Track how far it went against before hitting target
# avg_mae = mean of MAE across all winning trades
```

### UI Wireframe (replaces sparse 41.7% / 1.28 display)
```
┌──────────────────────────────────────────────────────────────────┐
│ 📈 PROBABILITY & BACKTEST QUALITY                                │
│                                                                   │
│  WIN RATE    PROFIT FACTOR   SHARPE    EXPECTANCY                │
│   41.7%         1.28          1.84      +$48/trade               │
│                                                                   │
│  ──────────────────────────────────────────────────────────────  │
│  MAX DRAWDOWN   MAX STREAK   SAMPLE    MAE (avg)                 │
│    -18.4%          4 L       n=127     2.8% against              │
│                                                                   │
│  ⚠️ CAUTION — Mixed signals. Reduce also 50%, Score 0.           │
└──────────────────────────────────────────────────────────────────┘
```

---

## Section 8 — Economic Calendar Pre-event Trigger (PRIORITY 8)

**Location:** Context Intelligence Panel — economic events card  
**Backend change:** `fundamentals_analyzer.py`

### Logic
```
If high_impact_event AND event_time is within 60 minutes:
  → risk_reduction_active = True
  → recommended_position_multiplier = 0.5
  → banner: "⏰ CPI in 23 min — Position size auto-reduced 50%"

If high_impact_event AND event_time is within 24 hours:
  → pre_event_caution = True
  → banner: "📅 NFP Tomorrow 08:30 ET — Reduce exposure before event"
```

### New fields in `FundamentalsAnalysis`
```
event_timestamps: List[{event: str, time_utc: str, impact: "HIGH"|"MEDIUM"}]
risk_reduction_active: bool
recommended_position_multiplier: float   # 1.0 = normal, 0.5 = reduce 50%
pre_event_caution: bool
minutes_to_next_event: Optional[int]
```

### UI Wireframe (extends existing economic events card in Column 3)
```
┌──────────────────────────────────────────────────────────────────┐
│ 📅 ECONOMIC EVENTS                                               │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ⏰ CPI RELEASE IN 23 MINUTES                              │   │
│  │ Position size auto-reduced 50% until event passes        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  🔴 CPI (US)         14:30 UTC    HIGH IMPACT                    │
│  🟡 FOMC Minutes     19:00 UTC    MEDIUM                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## Section 9 — Volume Spike / Block Alert (Dark Pool Approximation) (PRIORITY 9)

**Location:** Context Intelligence Panel — new `BLOCK FLOW` card  
**Backend change:** New logic in `strength_analyzer.py`

### Approximation (no dark pool feed)
```
Block alert condition:
  - Today's volume > 2.5x the 20-day average volume
  - Price moved < 0.5% (large volume, little price movement = absorption)
  → Signals institutional accumulation/distribution

  - Today's volume > 3x average AND price > 1% move
  → Directional block buying/selling
```

### New `BlockFlowAlert` model
```
is_alert: bool
volume_ratio: float          # e.g. 3.2x
alert_type: str              # "ABSORPTION" | "DIRECTIONAL" | "NONE"
direction: str               # "BUY" | "SELL" | "UNKNOWN"
description: str
```

### UI Wireframe (new card in Context Panel)
```
┌──────────────────────────────────────────────────────────────────┐
│ 🏦 BLOCK FLOW DETECTOR                                           │
│                                                                   │
│  Volume:  3.2x average         ELEVATED ACTIVITY                 │
│  Type:    ABSORPTION                                             │
│                                                                   │
│  Large volume with minimal price movement detected.              │
│  Possible institutional accumulation near $67,500.               │
│                                                                   │
│  Note: Approximate — based on volume anomaly, not dark pool.     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Responsive Behavior

All new sections follow existing patterns:
- Desktop (>1024px): Full layout in 3-column view
- Tablet (<1024px): Stacked, bottom nav shows Context tab
- Volume Profile histogram: SVG-based horizontal bars (no external chart library)
- Session VWAP table: 3-column grid, collapses to 1-column on mobile

---

## Implementation Order (Recommended)

| Priority | Feature | Impact | Effort |
|---|---|---|---|
| 1 | Conflicting Signal Resolution | Fixes critical UX bug | Low |
| 2 | ATR Percentile Rank / Volatility Regime | Replaces vague "MODERATE" | Low |
| 3 | Live Correlation Coefficients | Fixes "ANALYZING" placeholder | Low |
| 4 | MAE + Backtest Quality | Adds institutional-grade stats | Low |
| 5 | Economic Calendar Pre-event Trigger | Actionable risk management | Low |
| 6 | Volume Profile (POC/VAH/VAL) | Highest institutional value | Medium |
| 7 | Session VWAP | Pro entry timing | Medium |
| 8 | Liquidity Map | SMC-grade stop hunting view | Medium |
| 9 | Block Flow Detector | Volume anomaly alerts | Low |

---

## Confirmed Decisions

1. **Volume Profile** — 50 buckets for long-term strategy, 20 buckets for short-term strategy.
2. **Session VWAP** — Compute for currently selected instrument only (no extra batch calls).
3. **MAE** — Live backtest replay for long-term strategy; ATR-based estimate for short-term strategy.
4. **Liquidity Map** — Top 3 levels per side only.
5. **Block Flow** — Always visible in Context Intelligence Panel.

---

*Confirmed Mar 2026. Implementation proceeding in gui3.0 branch.*
