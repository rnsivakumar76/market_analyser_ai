# Market Analyser — Analysis Engine Documentation

> **Purpose**: Documents every calculation, formula, and decision rule used by the backend analysis engine, and explains how the Expert Battle Plan panel is produced. This is the single source of truth for understanding how the system derives trade signals.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Layers & Timeframes](#2-data-layers--timeframes)
3. [Layer 1 — Monthly Trend (Direction)](#3-layer-1--monthly-trend-direction)
4. [Layer 2 — Weekly Pullback (Timing)](#4-layer-2--weekly-pullback-timing)
5. [Layer 3 — Daily Strength (Confirmation)](#5-layer-3--daily-strength-confirmation)
6. [Signal Scoring & Hard Filters](#6-signal-scoring--hard-filters)
7. [ATR — Volatility & Trade Ranges](#7-atr--volatility--trade-ranges)
8. [Pivot Points](#8-pivot-points)
9. [Fibonacci Retracements & Extensions](#9-fibonacci-retracements--extensions)
10. [Volume Profile (VVRP)](#10-volume-profile-vvrp)
11. [Session VWAP](#11-session-vwap)
12. [Liquidity Map](#12-liquidity-map)
13. [Block Flow Detector](#13-block-flow-detector)
14. [Market Phase Classifier](#14-market-phase-classifier)
15. [Signal Conflict Detection](#15-signal-conflict-detection)
16. [Expert Battle Plan Panel](#16-expert-battle-plan-panel)
17. [How Everything Correlates — The Full Picture](#17-how-everything-correlates--the-full-picture)

---

## 1. Architecture Overview

The engine runs a **three-layer, scored analysis pipeline** per instrument. Every layer produces an independent signal, which feeds into a composite score. Hard filters then gate the score before a final `trade_worthy` flag is raised.

```
┌─────────────────────────────────────────────────────┐
│  DATA FETCHER  (TwelveData API + 4h cache layer)    │
│  Monthly/Weekly/Daily/Intraday bars per instrument  │
└─────────────────────────┬───────────────────────────┘
                          │
          ┌───────────────▼───────────────┐
          │       ANALYSIS PIPELINE       │
          │  Layer 1: Monthly Trend  40pt │
          │  Layer 2: Weekly Pullback 30pt│
          │  Layer 3: Daily Strength  30pt│
          └───────────────┬───────────────┘
                          │
          ┌───────────────▼───────────────┐
          │       5 HARD FILTERS          │
          │  1. ADX strength gate         │
          │  2. Benchmark beta alignment  │
          │  3. Candle pattern trigger    │
          │  4. Fundamental event guard   │
          │  5. Relative strength alpha   │
          └───────────────┬───────────────┘
                          │
          ┌───────────────▼───────────────┐
          │    RISK & CONTEXT OVERLAYS    │
          │  ATR  │ Pivots │ Fibonacci    │
          │  VWAP │ Vol Profile │ Liq Map │
          │  Block Flow │ Session Context │
          └───────────────┬───────────────┘
                          │
          ┌───────────────▼───────────────┐
          │   EXPERT BATTLE PLAN (SHORT   │
          │   TERM MODE ONLY)             │
          │  ORB + RVOL + Pivots + DXY    │
          └───────────────────────────────┘
```

**Source files involved:**
- `backend/app/main.py` — orchestration & caching
- `backend/app/signal_generator.py` — scoring engine & hard filters
- `backend/app/analyzers/` — one file per analytical module

---

## 2. Data Layers & Timeframes

The system fetches **three distinct timeframe datasets** per instrument, mapped to the strategy mode:

| Dataset | Long-Term Mode | Short-Term Mode | Cache TTL |
|---|---|---|---|
| **Macro** (trend) | `1month` bars, 1000 days | `1day` bars, 500 days | 4 hours |
| **Pullback** (timing) | `1week` bars, 250 days | `4h` bars, 120 days | 4 hours |
| **Execution** (confirmation) | `1day` bars, 500 days | `1h` bars, 300 days | Always fresh |
| **Expert** (intraday) | Not used | `15m` bars | Always fresh |

> **Cache strategy**: Macro and pullback data change slowly, so they are cached for 4 hours to avoid hitting TwelveData's 8 req/min rate limit. Execution data is always re-fetched for accuracy.

**Ideal Entry Price Anchoring** (`main.py` line ~260):  
Before calculating stops and targets, the system derives an `ideal_entry` price — the zone where it *expects* the trade to be entered, not the current price. This anchors ATR-based stops/targets to reality:

```
Bullish setup:  ideal_entry = min(S1, Fib 38.2%)
Bearish setup:  ideal_entry = max(R1, Fib 61.8%)
```

---

## 3. Layer 1 — Monthly Trend (Direction)

**File**: `analyzers/trend_analyzer.py`  
**Weight**: ±40 points in the composite score

### Formula

```
Fast MA  = SMA(Close, 20 periods)
Slow MA  = SMA(Close, 50 periods)

BULLISH  : Price > Fast MA  AND  Fast MA > Slow MA
BEARISH  : Price < Fast MA  AND  Fast MA < Slow MA
NEUTRAL  : Any mixed arrangement
```

### Interpretation

| Condition | Signal | Score |
|---|---|---|
| Price > 20MA > 50MA | BULLISH | +40 |
| Price < 20MA < 50MA | BEARISH | −40 |
| Mixed | NEUTRAL | 0 |

> When you see **"Weekly Up"** or **"Monthly Trend Bullish"** in the UI — this is the check being passed. All three must be stacked: price on top, fast MA in the middle, slow MA at the bottom.

---

## 4. Layer 2 — Weekly Pullback (Timing)

**File**: `analyzers/pullback_analyzer.py`  
**Weight**: Up to +30 points (bullish trend context only)

### Formula

```
recent_high       = max(High) over the pullback dataset
pullback_percent  = (recent_high − current_price) / recent_high

Swing supports    = local minima where lows[i] < lows[i-1] AND lows[i] < lows[i+1]
near_support      = distance_to_nearest_support / current_price <= 2%

pullback_detected = pullback_percent >= 3%  (configurable via instruments.yaml)
```

### Scoring in Bullish Trend

| Condition | Score |
|---|---|
| Pullback detected AND near support | +30 (ideal entry) |
| Pullback detected, NOT at support yet | +15 (wait) |
| No pullback (price extended from high) | +5 |

> In a **bearish trend**, a bounce to resistance adds −10 to −20 (short entry setup).

---

## 5. Layer 3 — Daily Strength (Confirmation)

**File**: `analyzers/strength_analyzer.py`  
**Weight**: ±30 points

This layer uses a **bullish-vs-bearish vote counter** across four sub-indicators. The majority wins.

### 5.1 RSI (Relative Strength Index)

```
delta  = Close.diff()
gain   = delta[delta > 0]  rolling(14).mean()
loss   = |delta[delta < 0]| rolling(14).mean()
RS     = gain / loss
RSI    = 100 − (100 / (1 + RS))

RSI < 30  → oversold  → +1 bullish vote
RSI > 70  → overbought → +1 bearish vote
```

### 5.2 VWAP (Volume Weighted Average Price)

```
Typical Price (TP)  = (High + Low + Close) / 3
VWAP                = Σ(TP × Volume) / Σ(Volume)  over last 20 bars
Distance %          = (current_price − VWAP) / VWAP × 100

distance > +1.5%  → price overextended above VWAP → +1 bearish vote
distance < −1.5%  → price at discount to VWAP    → +1 bullish vote
```

> VWAP is the **institutional fair value** anchor. Price below VWAP = cheap; above VWAP = expensive. The ±1.5% threshold is the mean-reversion trigger.

### 5.3 Volume Confirmation

```
volume_ratio = current_volume / SMA(volume, 20)

volume_ratio >= 1.5x  AND  price_change > 0  → +1 bullish vote (surge on up day)
volume_ratio >= 1.5x  AND  price_change < 0  → +1 bearish vote (surge on down day)
```

### 5.4 Price Action

```
daily_change > +1%  → +1 bullish vote (strong up day)
daily_change < −1%  → +1 bearish vote (strong down day)
```

### Final Daily Signal

```
bullish_votes > bearish_votes  → BULLISH  (+30 if trend aligned, +10 if against trend)
bearish_votes > bullish_votes  → BEARISH  (−30 if trend aligned, −10 if against trend)
tie                            → NEUTRAL  (0 points)
```

---

## 6. Signal Scoring & Hard Filters

**File**: `signal_generator.py`

### Composite Score

```
score = Layer1_trend + Layer2_pullback + Layer3_strength
Range: −100 (strong sell)  to  +100 (strong buy)
```

### Score → Recommendation Mapping

| Score | Recommendation | trade_worthy |
|---|---|---|
| >= conviction_threshold (default 70) | BULLISH | ✅ Yes |
| <= −70 | BEARISH | ✅ Yes |
| +20 to +69 | BULLISH (developing) | ❌ No |
| −20 to −69 | BEARISH (developing) | ❌ No |
| −19 to +19 | NEUTRAL | ❌ No |

### Hard Filter 1: ADX Trend Strength Gate

```
ADX (14)  = 14-period rolling mean of the Directional Index (DX)
DX        = 100 × |+DI − −DI| / (+DI + −DI)
+DI       = 100 × smoothed(+DM) / smoothed(TR)
−DI       = 100 × smoothed(−DM) / smoothed(TR)

ADX < threshold (default 25)  →  trade_worthy = False
                                  Reason: "Trend strength too low"
```

| ADX Range | Regime |
|---|---|
| < 20 | Ranging / Noise |
| 20–25 | Developing trend |
| 25–35 | Trending |
| > 35 | Strong trend |

> **ADX measures trend STRENGTH, not direction.** A high ADX means the market is moving decisively — doesn't say which way. Direction comes from +DI vs −DI.

### Hard Filter 2: Benchmark Beta (Market Alignment)

```
If recommendation == BULLISH  AND  benchmark (SPX/BTC) is BEARISH
    → trade_worthy = False  ("Beta Filter: avoid buying into a bearish market")

If recommendation == BEARISH  AND  benchmark is BULLISH
    → trade_worthy = False  ("Beta Filter: avoid shorting a bull market")
```

### Hard Filter 3: Candlestick Pattern Trigger

```
BULLISH setup requires: Hammer, Engulfing Bull, or other bullish reversal candle
BEARISH setup requires: Shooting Star, Engulfing Bear, or other bearish reversal candle

Missing candle confirmation → trade_worthy = False
                              Reason: "Trigger Filter: Waiting for confirmation candle"
```

### Hard Filter 4: Fundamental / Macro Event Guard

```
If high-impact economic event or earnings within 48h
    → trade_worthy = False
    → score adjusted by −20
    Reason: "Macro Shield Active"
```

### Hard Filter 5: Relative Strength (Alpha Shield)

```
BULLISH setup:  instrument must be OUTPERFORMING its benchmark (positive alpha)
BEARISH setup:  instrument must be UNDERPERFORMING (negative alpha)

Violation → trade_worthy = False
Reason: "Alpha Filter: instrument is a market laggard/leader"
```

---

## 7. ATR — Volatility & Trade Ranges

**File**: `analyzers/volatility_analyzer.py`

### ATR Formula (14-period)

```
True Range (TR) = max(
    High − Low,
    |High − Previous Close|,
    |Low  − Previous Close|
)

ATR = SMA(TR, 14)
```

### Stop Loss & Take Profit (Institutional Scaling Model)

All levels anchor to `ideal_entry` (see Section 2), not current price:

```
Bullish:
    SL   = entry − (ATR × 1.5)
    TP1  = entry + (ATR × 1.0)   ← De-risk: exit 30% here, move SL to breakeven
    TP2  = entry + (ATR × 2.0)   ← Core target: exit 40%
    TP3  = entry + (ATR × 3.0)   ← Runner: leave 30% or trail by 2× ATR

Bearish:
    SL   = entry + (ATR × 1.5)
    TP1  = entry − (ATR × 1.0)
    TP2  = entry − (ATR × 2.0)
    TP3  = entry − (ATR × 3.0)

Risk-Reward Ratio = 3.0 / 1.5 = 2.0
```

### ATR Volatility Regime (Percentile Rank)

```
ATR Percentile Rank = percentile rank of current ATR vs all historical ATR values

<= 25th pct  → LOW      ("Compressed")   — tight stops possible
26–60th pct  → NORMAL   ("Normal")       — standard sizing
61–80th pct  → ELEVATED ("Expanding")   — reduce size
> 80th pct   → EXTREME  ("Extreme")     — extreme caution, widen stops
```

Additionally, a **14-day Historical Volatility (HV)** is computed:
```
HV_14 = std(log(Close / Close.shift(1)), 14 bars) × sqrt(252) × 100
```

---

## 8. Pivot Points

**File**: `analyzers/technical_analyzer.py`

Standard pivot point formula derived from the **previous complete bar** (yesterday's OHLC):

```
Pivot (P)  = (High + Low + Close) / 3

R1 = (2 × P) − Low          S1 = (2 × P) − High
R2 = P + (High − Low)       S2 = P − (High − Low)
R3 = High + 2(P − Low)      S3 = Low − 2(High − P)
```

### How Pivots Are Used

| Level | Role |
|---|---|
| **Pivot** | Daily fair value / decision line |
| **S1, S2** | Expected support zones; pullback entry targets |
| **R1, R2** | Expected resistance zones; TP levels and pyramid triggers |
| **S3, R3** | Extreme extension levels |

The system also uses pivots for:
- **Action Plan**: "Ideal entry is on a pullback near S1" or "Target R1 for first exit"
- **Pyramiding**: "Add 50% to position IF price holds above R1 AND RSI < 70"
- **Signal Conflict**: R1 and S1 are used as breakout confirmation triggers

### Line of Least Resistance

```
Uses linear regression (polyfit) over last 20 closes:
slope / last_price > +0.1%/bar → "up"
slope / last_price < −0.1%/bar → "down"
otherwise                      → "flat"
```

### Donchian Channel Breakout

```
upper_band = max(High) of previous 20 bars
lower_band = min(Low)  of previous 20 bars

Close > upper_band  → bullish_breakout, confidence = min(vol_ratio / 2, 1.0)
Close < lower_band  → bearish_breakout
```

---

## 9. Fibonacci Retracements & Extensions

**File**: `analyzers/technical_analyzer.py`

Uses the **last 60 bars** to identify the swing high and swing low:

```
diff  = swing_high − swing_low

If current_price closer to high (uptrend):
    ret_382  = high − (diff × 0.382)    ← ideal entry zone for pullback
    ret_500  = high − (diff × 0.500)    ← deeper pullback
    ret_618  = high − (diff × 0.618)    ← maximum acceptable pullback (golden ratio)
    ext_1272 = low  + (diff × 1.272)    ← first extension target
    ext_1618 = low  + (diff × 1.618)    ← final extension target (golden ratio extension)

If current_price closer to low (downtrend):
    ret_382  = low  + (diff × 0.382)    ← bounce resistance
    ret_618  = low  + (diff × 0.618)    ← deep bounce resistance
    ext_1618 = high − (diff × 1.618)    ← extension target for shorts
```

### RSI Divergence (Trend Reversal Warning)

```
Compares price and RSI between the midpoint and the current bar over 20 bars:

Bearish divergence: price makes higher high (+0.5%), RSI makes lower high (−3 pts)
                   → potential reversal down

Bullish divergence: price makes lower low (−0.5%), RSI makes higher low (+3 pts)
                   → potential reversal up
```

---

## 10. Volume Profile (VVRP)

**File**: `analyzers/volume_profile_analyzer.py`

Builds a histogram of **where volume traded** across the price range:

```
Long-term mode:  50 buckets across full history
Short-term mode: 20 buckets across last 20 bars

For each candle:
    overlap with each bucket = min(High, bucket_top) − max(Low, bucket_bottom)
    volume assigned to bucket += candle_volume × (overlap / candle_range)

POC (Point of Control) = bucket with highest assigned volume
                        → acts as a price magnet / mean-reversion target

Value Area = 70% of total volume (expand from POC outward until 70% captured)
    VAH (Value Area High) = upper edge of value area
    VAL (Value Area Low)  = lower edge of value area
```

### Interpretation

| Price vs Value Area | Meaning |
|---|---|
| Price > VAH | Breakout zone — watch for continuation or rejection |
| Price < VAL | Breakdown zone — high acceptance risk below |
| VAL < Price < VAH | Mean-reversion bias toward POC |

> **POC is where institutions did the most business.** Price tends to gravitate back to POC, making it a key level for entries, stops, and targets.

---

## 11. Session VWAP

**File**: `analyzers/session_vwap_analyzer.py`

Intraday VWAP calculated fresh for the **current trading session** (1h or 15m bars):

```
Filter to today's bars (or last 24 bars if timezone unavailable)

Typical Price (TP) = (High + Low + Close) / 3

Cumulative VWAP = Σ(TP × Volume) / Σ(Volume)  — running sum from session open

Upper Band = VWAP + std(TP − VWAP)   ← +1σ
Lower Band = VWAP − std(TP − VWAP)   ← −1σ

Distance % = (current_price − VWAP) / VWAP × 100
```

### Position Interpretation

| Distance | Position | Bias |
|---|---|---|
| > +1.5% | EXTENDED ABOVE | Avoid chasing longs; wait for VWAP pullback |
| 0 to +1.5% | ABOVE | Bullish session bias; VWAP = dynamic support |
| −1.5% to 0 | BELOW | Bearish session bias; VWAP = dynamic resistance |
| < −1.5% | EXTENDED BELOW | Oversold vs session mean; mean-reversion entry |

> **Session VWAP differs from the 20-bar VWAP** used in Daily Strength. Session VWAP resets at the open of each trading day and reflects intraday institutional fair value.

---

## 12. Liquidity Map

**File**: `analyzers/liquidity_map_analyzer.py`

Identifies **where stop-loss clusters exist** by mapping swing highs/lows and round numbers:

```
Swing Highs: local maxima where High[i] = max(High[i−5 : i+5])
Swing Lows:  local minima where Low[i]  = min(Low[i−5 : i+5])

Round numbers: generated at 1% price-magnitude steps
    (e.g., for a $2,800 asset: $2,800, $2,825, $2,850, ...)

Clustering: merge levels within 0.5% of each other (take mean)

Resistance levels = swing highs + round numbers ABOVE current price
Support levels    = swing lows  + round numbers BELOW current price

Top 3 per side displayed (ordered by proximity to current price)

Strength rating:
    touches >= 3  → "strong"
    touches >= 2  → "moderate"
    otherwise     → "weak"
```

> **Why liquidity matters**: Large stop-loss orders cluster below swing lows and above swing highs. Institutions deliberately push price into these zones to fill their own orders (a "stop hunt"). Knowing these levels helps anticipate fake breakouts and real breakouts.

---

## 13. Block Flow Detector

**File**: `analyzers/block_flow_analyzer.py`

Detects **institutional accumulation or distribution** by identifying abnormal-volume candles with significant price movement:

```
20-bar average volume = SMA(Volume, 20)

A candle qualifies as a "block" if:
    volume >= 2.5 × average_volume    (institutions moved size)
    AND
    body_ratio = |Close − Open| / ATR >= 0.4   (not a doji/noise bar)

Direction:
    Close >= Open → bullish block (buying)
    Close <  Open → bearish block (selling)

Net Direction = majority of last 5 qualifying blocks

bull_count > bear_count → net bullish (institutional accumulation)
bear_count > bull_count → net bearish (institutional distribution)
```

---

## 14. Market Phase Classifier

**File**: `analyzers/phase_analyzer.py`

Identifies the **Wyckoff-style market phase** using MA20, MA50, and the 5-bar slope of MA50:

```
ma50_slope = (current_MA50 − MA50[5 bars ago]) / MA50[5 bars ago]

If ma50_slope > +0.5% (rising):
    Price > MA20 > MA50                → MARKUP    (demand > supply)
    Otherwise                          → DISTRIBUTION (stalling)

If ma50_slope < −0.5% (falling):
    5-day price drop > 8%              → LIQUIDATION  (panic selling)
    Price < MA20 AND MA20 < MA50       → MARKDOWN     (supply > demand)
    Otherwise                          → ACCUMULATION (bottoming)

If ma50_slope flat (±0.5%):
    MA20 > MA50                        → DISTRIBUTION (topping out)
    MA20 < MA50, price > MA20          → ACCUMULATION (demand picking up)
    Otherwise                          → CONSOLIDATION (no clear winner)
```

---

## 15. Signal Conflict Detection

**File**: `signal_generator.py`

Automatically detects and explains contradictions in the signal, preventing false confidence:

### Conflict Type 1: ADX/Direction Mismatch

```
Trigger: ADX >= 35 (strong trend confirmed) BUT recommendation == NEUTRAL

Severity: HIGH
Message: "ADX=XX confirms LOCKED TREND — but directional bias is NEUTRAL"
Action:  "Watch: break above R1 to confirm BULLISH, or break below S1 to confirm BEARISH"
```

### Conflict Type 2: Multi-Timeframe Disagreement

```
Trigger A: Monthly = BULLISH, Daily = BEARISH
Severity: MEDIUM
Message: "MTF Conflict: Monthly BULLISH vs Daily BEARISH momentum"
Action:  "Dip-buy setup — wait for daily to stabilise before adding exposure"

Trigger B: Monthly = BEARISH, Daily = BULLISH
Severity: MEDIUM
Message: "MTF Conflict: Monthly BEARISH vs Daily BULLISH momentum"
Action:  "Dangerous dead-cat bounce — avoid buying unless monthly trend reverses"
```

---

## 16. Expert Battle Plan Panel

**Files**: `analyzers/day_trading_expert.py`, `signal_generator.py`, `main.py`  
**UI**: `frontend/.../instrument-card.component.ts` — `expert-above-tabs` section  
**Mode**: **Short-Term mode only** (requires 15-minute intraday data)

The Expert Battle Plan is displayed as a **prominent banner above all tabs** in the instrument card. It is updated with every refresh and shows its age (stale if > 30 min).

---

### 16.1 Opening Range Breakout (ORB)

```
Opening Range = High and Low of the FIRST 15-minute candle of the current trading day

or_high = daily_data.iloc[0]['High']
or_low  = daily_data.iloc[0]['Low']

broken = "bullish"  if current_price > or_high  (breakout up)
broken = "bearish"  if current_price < or_low   (breakout down)
broken = "none"     if price inside range        (no signal yet)
```

> The opening range is the **opening battle** between bulls and bears. A clean breakout above `or_high` with volume signals the daily trend direction.

---

### 16.2 RVOL — Relative Volume

```
RVOL = current_bar_volume / average_volume_at_same_time_over_last_5_days

(Compares this 15m bar's volume to the SAME 15m bar historically — far more
accurate than a simple rolling MA for day trading)

RVOL >= 1.8x → is_high_intent = True  (institutions active)
RVOL >= 2.0x → "HIGH CONVICTION" plan entry
```

---

### 16.3 DXY & Yield Correlation (Commodity-Specific Logic)

```
DXY change  = (DXY_close_now − DXY_close_prev) / DXY_close_prev × 100
Yield change = same for US10Y

XAU/GOLD:
    DXY rising  AND  yields rising   → "WARNING: Gold longs are HIGH RISK (Bull Trap)"
    DXY falling AND  yields falling  → "EXPERT: Gold 'God-Candle' potential — focus on longs"

WTI/OIL:
    Wednesday (EIA day)              → "Expect high-volatility flush at 10:30 AM EST"

BTC:
    DXY spike > +0.3%                → "Crypto liquidity might dry up — tighten stops"
```

---

### 16.4 Battle Plan Generation Logic

The plan is assembled as a pipe-separated string of actionable instructions:

```
Step 1 — ORB Direction:
    or_broken == "bullish" → "ORB BULLISH: Price held above {or_high}. Trend is UP."
    or_broken == "bearish" → "ORB BEARISH: Price broke below {or_low}. Trend is DOWN."

Step 2 — RVOL Confirmation:
    rvol > 2.0 → "HIGH CONVICTION: RVOL is {rvol}x. Institutions are active."

Step 3 — Pivot Targets with signal alignment check:
    ORB bullish + signal BEARISH  → "CAUTION: Bullish ORB against bearish signal.
                                     R1 ({r1}) is resistance to fade."
    ORB bearish + signal BULLISH  → "PULLBACK IN PROGRESS: Watch for long reversal at S1."
    ORB bullish + signal aligned  → "TARGETS: Aim for R1 ({r1}) then R2 ({r2})."
    Price below pivot, BULLISH    → "PULLBACK ZONE: Watch for long entry near S1."

Step 4 — Fibonacci entry zone (bearish ORB in bullish trend):
    "KEY ENTRY: Fib 38.2% at {ret_382} is the ideal long trigger zone."

Step 5 — Commodity-specific expert advice (if applicable)

Final output:  " | ".join(all plan steps)
```

---

### 16.5 UI Rendering (`instrument-card.component.ts`)

| Field | Display |
|---|---|
| `battle_plan` | Full text of the assembled plan |
| `rvol` | Badge: "RVOL 2.3x 🔥" (orange if >= 1.8x) |
| `is_high_intent` | Orange border + glow animation on the card |
| `or_high / or_low` | Used by ORB Dashboard for market-wide ORB view |
| `plan_age` | Timestamp label; turns red if > 30 minutes old |

---

## 17. How Everything Correlates — The Full Picture

The following diagram shows how each module's output **feeds into the next**:

```
MACRO TREND (20MA / 50MA)
│
├─ Sets DIRECTIONAL BIAS (±40 pts)
├─ Determines PHASE (Markup / Markdown / Accumulation / etc.)
└─ Informs SIGNAL CONFLICT checker

WEEKLY PULLBACK (swing high/low, 3% threshold)
│
├─ Times the ENTRY (±30 pts)
├─ Identifies SUPPORT LEVELS for SL anchoring
└─ Interacts with FIBONACCI (38.2% / 61.8% as entry zones)

DAILY STRENGTH (RSI + VWAP + Volume + Price Change)
│
├─ Confirms MOMENTUM (±30 pts)
├─ RSI divergence → warns of trend REVERSAL
└─ VWAP distance → detects overextension before entry

ADX (trend strength gate)
│
├─ Must be > 25 for trade_worthy = True
└─ ADX >= 35 triggers conflict check if direction is NEUTRAL

PIVOT POINTS (prev session OHLC)
│
├─ S1/S2 → pullback entry targets
├─ R1/R2 → TP1 and pyramid trigger levels
└─ Pivot midpoint → action plan phrasing

ATR (14-period true range average)
│
├─ SL  = entry ± 1.5× ATR
├─ TP1 = entry ± 1.0× ATR
├─ TP2 = entry ± 2.0× ATR
└─ TP3 = entry ± 3.0× ATR  (Risk/Reward = 2:1)

FIBONACCI (last 60-bar swing)
│
├─ 38.2% retracement → wait-for-entry zone (ideal_entry calculation)
├─ 61.8% retracement → bearish entry anchor
└─ 1.618 extension   → runner target

VOLUME PROFILE (POC / VAH / VAL)
│
├─ POC acts as gravity / mean-reversion magnet
├─ Price above VAH → breakout mode
└─ Price inside VA → mean-reversion mode

SESSION VWAP (intraday reset)
│
├─ ±1.5% bands → intraday overextension trigger
└─ VWAP line → dynamic S/R for same-day entries

LIQUIDITY MAP (swing highs/lows + round numbers)
│
├─ Shows where stop hunts are likely
└─ Clustered resistance = high-risk zone for entries

BLOCK FLOW (2.5× vol + significant body)
│
└─ Net direction → confirms or contradicts trend

INTERMARKET (DXY / US10Y)          [Short-term mode only]
│
└─ Expert advice for Gold, Oil, BTC

OPENING RANGE BREAKOUT + RVOL      [Short-term mode only]
│
└─ Expert Battle Plan panel
```

### The Decision Hierarchy in Plain English

1. **Is the macro trend aligned?** (MA stack) → Sets direction
2. **Has price pulled back to value?** (swing support / Fib 38.2%) → Identifies timing
3. **Is momentum confirming?** (RSI not overbought, price near VWAP, volume surging) → Validates entry
4. **Is the trend actually moving?** (ADX > 25) → Filters ranging markets
5. **Is the broader market supportive?** (benchmark direction, relative strength) → Avoids fighting the tide
6. **Has price shown intent?** (candle pattern trigger) → Confirms execution point
7. **Any macro landmines?** (economic events) → Avoids news explosions
8. **What are the exact levels?** (ATR stops, Pivot targets, Fib extensions) → Structures the trade
9. **Where is institutional money?** (Volume Profile POC, Block Flow, Liquidity Map) → Finds high-probability zones
10. **Intraday: what is the battle plan?** (ORB + RVOL + DXY correlation) → Day trading execution guide
