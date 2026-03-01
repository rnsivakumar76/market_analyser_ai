# Market Analyzer AI — Wireframes v3.0 (Layout Redesign)

**Design Date**: March 1, 2026  
**Revision**: v3.0 — Layout Optimisation based on User Review Session  
**Status**: ✅ CONFIRMED — Ready for Implementation  

---

## 📋 DESIGN DECISIONS SUMMARY (v2.0 → v3.0)

| # | Area | v2.0 (Current) | v3.0 (Proposed) | Reason |
|---|---|---|---|---|
| 1 | Column 3 | Performance & Status always visible | Context Intelligence Panel | Perf stats repetitive; column 3 better used for contextual data |
| 2 | Performance & Status | Permanent 3rd column | Accessible via 📒 Journal header button (modal/slide-out) | Not always needed on screen |
| 3 | Geopolitical Tab | Separate tab in middle | Removed — content lives in Column 3 | Column 3 is the natural home for market intelligence |
| 4 | Scaling Tab | Separate tab | Content merged into TECHNICAL tab as **first section** | Trade execution belongs with technical analysis |
| 5 | Pivot Matrix | In Geopolitical tab | Moved into TECHNICAL tab, below Scaling | Always needed as reference range |
| 6 | Technical Tab | Expert Battle Plan, Macro, Heat | Expanded: Scaling → Pivot Matrix → AI Reasoning → Technical | Single complete analysis view |
| 7 | AI Trade Reasoning | Not present | New section under TECHNICAL | Explains WHY bullish/bearish with indicator evidence |
| 8 | Risk Tab layout | Validation + Pullback stacked | Side-by-side 2-card layout | Pullback risk is critical, needs equal visual weight |
| 9 | Tab structure | TECHNICAL · GEOPOLITICAL · RISK · SCALING · PERFORMANCE · SETTINGS | **TECHNICAL · RISK** | Cleaner — fewer tabs, all content accessible |
| 10 | Settings Tab | Separate tab | Removed — ⚙️ header button (already exists) | Already accessible, no tab needed |
| 11 | Performance Tab | Separate tab | Removed — 📒 Journal header button opens Performance modal | Already accessible |
| 12 | Intelligence Viewer | Below tabs in middle column | Moved to Column 3, below Market Intelligence | Belongs with news/context content |

---

## 🖥️ DESKTOP WIREFRAME (1920×1080)

### Column Layout Overview
```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ NEXUS PRO  [👤 User]  [🛡️ Shield]  [📊 Correlation]  [📖 Manual]  [⚡ Strategy]  [⚙️ Settings→modal]      │
│            [📒 Journal/Performance→modal]  [🔔 Alerts]  [🌍 Geopolitical→modal]  [Mode 📅]  [🔄 Refresh]   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────┐  ┌──────────────────────────────────────────────────────────┐  ┌─────────────────────┐ │
│ │  COLUMN 1        │  │  COLUMN 2 — CRITICAL DECISION AREA                        │  │  COLUMN 3           │ │
│ │  Watchlist (~280)│  │  (flex:1 — takes remaining width)                         │  │  Context Intel (~280│ │
│ │  Heatmap         │  │                                                            │  │  Panel)             │ │
│ └──────────────────┘  └──────────────────────────────────────────────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### COLUMN 1 — Watchlist Heatmap (unchanged)
```
┌──────────────────────┐
│ WATCHLIST HEATMAP    │
│                      │
│ ┌──────┐ ┌──────┐   │
│ │ BTC  │ │ XAU  │   │
│ │+1.38%│ │-0.22%│   │
│ │BULL  │ │NEUT  │   │
│ └──────┘ └──────┘   │
│ ┌──────┐ ┌──────┐   │
│ │ AAPL │ │ TSLA │   │
│ │+0.85%│ │-1.20%│   │
│ └──────┘ └──────┘   │
│                      │
│ ↑ 4  Bullish         │
│ ↓ 2  Bearish         │
│ ⚡ 3  Trade-worthy    │
└──────────────────────┘
```

---

### COLUMN 2 — Critical Decision Area

```
┌────────────────────────────────────────────────────────────────────────────┐
│ MULTI-TIMEFRAME ALIGNMENT                                  [→ PARTIAL]      │
│                                                                              │
│  PRIMARY TREND      STRUCTURE PHASE    INTERMEDIATE         TACTICAL DAILY  │
│  (Monthly)          (Phase)            STATE (Weekly)       (Momentum)      │
│  ┌──────────┐  →   ┌──────────┐  →   ┌──────────────┐ → ┌──────────────┐  │
│  │ NEUTRAL  │      │ NEUTRAL  │      │   BULLISH    │   │   BULLISH    │  │
│  │Institutional│   │Accumulation│    │   Pullback   │   │   Execution  │  │
│  └──────────┘      └──────────┘      └──────────────┘   └──────────────┘  │
│  Timeframes show partial alignment — exercise selectivity and manage size   │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  BTC  $67,893.05  +1.38%                         [10 neutral] [💬]         │
│  [☑ ] [ASIA] [Clean Calendar]                                               │
│                                                                              │
│  ⚡ AI EXECUTIVE SUMMARY                                                     │
│  The system advises staying sidelined right now due to mixed or conflicting  │
│  signals. The macro (long-term) picture is currently in sideways             │
│  consolidation. Conclusion: Wait patiently for better mathematical           │
│  alignment or a clearer setup before taking action.                          │
│                                                                              │
│  [#Monthly trend unclear] [#Daily bullish but against trend]                │
│  [#No clear setup — wait]  [#Trend strength high (ADX=38.1)]               │
└────────────────────────────────────────────────────────────────────────────┘

  ┌────────────┐  ┌───────────────────────────────────────────────────────┐
  │ TECHNICAL  │  │  RISK                                                  │
  └────────────┘  └───────────────────────────────────────────────────────┘
  ───────────────────────────────────────────────────────────────────────────
```

---

#### TECHNICAL TAB (Expanded — 4 sections, top to bottom)

```
┌── SECTION 1: STRATEGIC ACTION & SCALING ─────────────────────────────────────┐
│                                                                                │
│  Wait and Observe                                                              │
│  Neutral bias. Key zones: R1 ($68,813.07) and S1 ($64,071.12)                │
│                                                                                │
│  ┌─────────────────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ ENTRY                   │  │ STOP         │  │ TARGET                 │  │
│  │ $64,071.12 – 74,502.72  │  │ $63,764.81   │  │ $76,149.53             │  │
│  └─────────────────────────┘  └──────────────┘  └────────────────────────┘  │
│                                                                                │
│  ┌── VISUAL R/R DIAGRAM ──────────────────────────────────────────────────┐  │
│  │                                                                          │  │
│  │  [TARGET] ────────────────────────────────────────────────── $76,149.53 │  │
│  │       ▲ +$12,078.41 REWARD                                               │  │
│  │  [ENTRY ▼] ────────────────────────────────────────── $64,071–74,502.72 │  │
│  │       ▼ -$306.31 RISK                                                    │  │
│  │  [STOP]  ────────────────────────────────────────────────── $63,764.81  │  │
│  │                                                                          │  │
│  │  R/R RATIO     PROBABILITY    EXP VALUE      ACC RISK                   │  │
│  │  39.43:1       41.7%          +$4,858.12     $300.00                    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  FIXED SCALING ENTRIES (50 / 30 / 20)                                        │
│  ┌───────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │
│  │ 50% ALLOC Tactical    │  │ 30% ALLOC Base Profit│  │ 20% Infinite Run │  │
│  │ $70,645.21            │  │ $73,397.37           │  │ $76,149.53       │  │
│  └───────────────────────┘  └─────────────────────┘  └──────────────────┘  │
│  LOT: 0.07    RISK: $300.00    TRAIL STOP: —                                 │
│                                                                                │
│  [📒 Log Trade]                              [📊 Open Chart]                  │
└────────────────────────────────────────────────────────────────────────────────┘

┌── SECTION 2: PIVOT MATRIX & EXTENSIONS ──────────────────────────────────────┐
│                                                                                │
│  R3: $73,555.02     R2: $70,658.28     R1: $68,813.07                        │
│                  P:  $65,016.33                                                │
│  S1: $64,071.12     S2: $61,174.38     S3: $59,320.17                        │
│                                                                                │
│  LOWEST 52W: $49,675.17                    HIGHEST 52W: $36,540.10           │
└────────────────────────────────────────────────────────────────────────────────┘

┌── SECTION 3: AI TRADE REASONING ─────────────────────────────────────────────┐
│                                                                                │
│  WHY THIS TRADE IS CONSIDERED [BULLISH / BEARISH / NEUTRAL]                  │
│                                                                                │
│  BULLISH FACTORS:                                                              │
│  • Daily momentum locked upward — ADX=38.1 (ultra-strong trend)              │
│    ADX above 25 confirms trend is active, not a false signal.                 │
│  • Price positioned above S1 pivot ($64,071) — structure intact              │
│    Key support holding; pullback is within healthy correction range.          │
│  • Weekly timeframe in pullback within a bull trend (entry zone)             │
│    Pullback to weekly support historically resolves to continuation.          │
│                                                                                │
│  BEARISH / CAUTION FACTORS:                                                   │
│  • Monthly trend: NEUTRAL / Accumulation — no macro confirmation yet         │
│    Large institutions not positioned — adds execution risk.                   │
│  • RSI=45 — neutral, not oversold — no confirmation of reversal yet          │
│  • MACD below signal line — momentum not yet confirmed bullish               │
│                                                                                │
│  NEXT RANGE ESTIMATE:                                                          │
│  ▲ UP SCENARIO:   $68,813 (R1) → $70,658 (R2) → $73,555 (R3)               │
│    Trigger: Break and close above $67,500 with ADX rising                    │
│  ▼ DOWN SCENARIO: $64,071 (S1) → $61,174 (S2)                               │
│    Trigger: Close below pivot $65,016 on volume                              │
│                                                                                │
│  DATA USED: ADX=38.1 · RSI=45 · MACD Signal Cross · Pivot P=$65,016        │
└────────────────────────────────────────────────────────────────────────────────┘

┌── SECTION 4: TECHNICAL ANALYSIS ─────────────────────────────────────────────┐
│                                                                                │
│  ┌── EXPERT BATTLE PLAN ──────────────────────────────────────────────────┐  │
│  │  Current technical approach and action context (existing section)       │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌── MACRO REGIME ──┐  ┌── TECHNICAL HEAT ──────────────────────────────┐  │
│  │  (existing)       │  │  ADX: 38.1 [STRONG]   RSI: 45 [NEUTRAL]        │  │
│  └───────────────────┘  │  Trade Impact: MEDIUM                           │  │
│                          └────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌── ECONOMIC DATA ───────────────────────────────────────────────────────┐  │
│  │  (instrument-specific upcoming economic events — existing section)      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

#### RISK TAB — Side-by-side 2-card layout

```
┌── RISK TAB ──────────────────────────────────────────────────────────────────┐
│                                                                                │
│  ┌── VALIDATION & RISK INTEL ───────────────┐  ┌── PULLBACK & TRAP ANALYSIS ─┐│
│  │                                          │  │                             ││
│  │  TREND STRUCTURE          NEUTRAL        │  │  ⚠️ PULLBACK WARNING        ││
│  │  Consolidation phase. Wait for breakout. │  │  Price near resistance with ││
│  │                                          │  │  bearish divergence         ││
│  │  MOMENTUM (ADX)               38         │  │                             ││
│  │  Ultra-Strong Trend locked.              │  │  RISK LEVEL                 ││
│  │                                          │  │  HIGH                       ││
│  │  VOLATILITY RISK         MODERATE        │  │                             ││
│  │  Affects position sizing.                │  │  CURRENT POSITION           ││
│  │                                          │  │  NEAR RESISTANCE            ││
│  │  VOLUME ANALYSIS         ANALYZING       │  │                             ││
│  │  Trap Alert: Zero institutional support  │  │  RECOMMENDED ACTION         ││
│  │                                          │  │  HOLD POSITION              ││
│  │  KEY LEVELS          ABOVE PIVOT         │  │                             ││
│  │  Price above pivot — key levels noted.   │  │  ◈ RSI divergence          ││
│  │                                          │  │  ◈ Volume drying up        ││
│  │  MARKET CORRELATION      ANALYZING       │  │  ◈ Resistance at R1        ││
│  │  Correlation analysis in progress.       │  │                             ││
│  └──────────────────────────────────────────┘  └─────────────────────────────┘│
│                                                                                │
│  ┌── PROBABILITY DEPTH (BACKTEST) ───────────────────────────────────────┐   │
│  │  WIN RATE: 41.7%    PROFIT FACTOR: 1.28                                │   │
│  │  ▁▂▃▄▅▆▇█▇▆▅▄▃ (equity curve sparkline)                               │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────┘
```

---

### COLUMN 3 — Context Intelligence Panel (new design)

```
┌─────────────────────────────────────┐
│ CONTEXT INTELLIGENCE                │
├─────────────────────────────────────┤
│                                     │
│  📅 ECONOMIC EVENTS — NEXT 24H      │
│  Specific to: BTC / USD             │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ 🔴 HIGH IMPACT                │  │
│  │ CPI (USD)   09:30 EST Today   │  │
│  │ Forecast: 3.1%  Prev: 3.4%   │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ 🔴 HIGH IMPACT                │  │
│  │ FOMC Minutes  14:00 EST       │  │
│  │ USD — Market expects hold     │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ 🟡 MEDIUM IMPACT              │  │
│  │ Initial Jobless Claims 08:30  │  │
│  │ Forecast: 215K  Prev: 218K   │  │
│  └───────────────────────────────┘  │
│                                     │
├─────────────────────────────────────┤
│                                     │
│  🌍 MARKET INTELLIGENCE             │
│  Geopolitical + Sentiment           │
│  Impact scored for: BTC             │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ 📰 NEWS SEARCH      4h ago   │  │
│  │ BTC surpasses $67,000 —      │  │
│  │ record institutional buys.    │  │
│  │ [Bullish ●]    Impact: +65   │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ 📰 NEWS SEARCH     14h ago   │  │
│  │ Iran-US tensions escalate.   │  │
│  │ $12B wiped from crypto.      │  │
│  │ [Bearish ●]    Impact: -85   │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ 📰 NEWS SEARCH      4h ago   │  │
│  │ Strategy Inc. 100th BTC buy. │  │
│  │ MicroStrategy reinforces.    │  │
│  │ [Bullish ●]    Impact: +45   │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │ 📰 NEWS SEARCH     11h ago   │  │
│  │ Marathon Digital Q4 loss.    │  │
│  │ MARA +15% on AI partnership. │  │
│  │ [Neutral ●]    Impact: +10   │  │
│  └───────────────────────────────┘  │
│                                     │
│  NET SENTIMENT SCORE: NEUTRAL (0)   │
│  Based on 10 recent headlines       │
│                                     │
├─────────────────────────────────────┤
│                                     │
│  🔍 INTELLIGENCE VIEWER             │
│                                     │
│  [News Search]                      │
│  XAU Market Performance Analysis   │
│  — Stock Traders Daily              │
│  — GoldMoney Inc. (XAU:CA)         │
│  Recent Articles Feb 25, 2026       │
│                                     │
│  Sentiment: Neutral (Score: 0.00)   │
│  Direct embedded viewing blocked    │
│  by provider security settings.     │
│  [Read Full Article on News →]      │
│                                     │
└─────────────────────────────────────┘
```

---

## 📱 TABLET WIREFRAME (1024×768)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ NEXUS PRO  [👤] [🛡️] [📊] [⚡] [⚙️] [📒] [🔔] [🌍] [Mode 📅] [🔄]         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌──────────────────────┐  ┌───────────────────────────────────────────────┐ │
│  │ WATCHLIST HEATMAP    │  │  CRITICAL DECISION AREA                       │ │
│  │                      │  │                                               │ │
│  │ [BTC] [XAU] [AAPL]  │  │  Multi-Timeframe: PARTIAL alignment           │ │
│  │ ↑ 4 Bullish          │  │  BTC $67,893  +1.38%   [10 neutral]          │ │
│  │ ↓ 2 Bearish          │  │  AI: Wait patiently for better alignment      │ │
│  │ ⚡ 3 Trade-worthy     │  │                                               │ │
│  └──────────────────────┘  │  [TECHNICAL]  [RISK]                          │ │
│                             │  ─────────────────────────────────────────── │ │
│                             │  TECHNICAL TAB:                               │ │
│                             │  Section 1: Strategic Action & Scaling        │ │
│                             │  Section 2: Pivot Matrix                      │ │
│                             │  Section 3: AI Trade Reasoning                │ │
│                             │  Section 4: Technical Analysis                │ │
│                             └───────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  CONTEXT INTELLIGENCE (collapsed accordion — tap to expand)             │ │
│  │  [📅 Economic Events (2 high impact)] [🌍 Market News (4)] [🔍 Intel]   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 MOBILE WIREFRAME (375×667)

```
┌──────────────────────────────────────┐
│ NEXUS PRO  [👤] [🛡️] [⚙️] [🔄]      │
├──────────────────────────────────────┤
│                                      │
│ BTC $67,893  +1.38%  [10 neutral]   │
│ ⚡ AI: Wait — mixed signals          │
│ [#Monthly unclear] [#ADX=38.1]      │
│                                      │
│ ┌────────────────────────────────┐  │
│ │  Multi-Timeframe: PARTIAL       │  │
│ │  Monthly NEUTRAL → Daily BULL  │  │
│ └────────────────────────────────┘  │
│                                      │
│ [TECHNICAL]  [RISK]  [📅 Events]    │
│ ──────────────────────────────────  │
│                                      │
│  TECHNICAL TAB (scrollable):        │
│                                      │
│  ─ Strategic Action & Scaling ─     │
│  Wait and Observe                   │
│  Entry: $64,071   Stop: $63,764    │
│  Target: $76,149  R/R: 39.4:1      │
│  [Visual R/R Diagram — compact]     │
│                                      │
│  ─ Pivot Matrix ─                   │
│  R1: $68,813   P: $65,016          │
│  S1: $64,071                        │
│                                      │
│  ─ AI Trade Reasoning ─             │
│  Bullish: ADX=38.1 trend locked    │
│  Caution: RSI=45 neutral            │
│  Up: →$68,813  Down: →$64,071     │
│                                      │
│  ─ Technical Analysis ─             │
│  ADX: 38.1 [STRONG]                │
│  RSI: 45 [NEUTRAL]                 │
│  MACD: Below signal                 │
│                                      │
│ ─────────────────────────────────── │
│                                      │
│  📅 EVENTS (next 24h — compact)     │
│  🔴 CPI (USD) 09:30 — Fcst 3.1%   │
│  🔴 FOMC Min 14:00                 │
│                                      │
│  🌍 NEWS CARDS (swipeable row)      │
│  [Bullish +65][Bearish -85][+45]   │
│                                      │
└──────────────────────────────────────┘
```

---

## 🗂️ SECTION-BY-SECTION SPECIFICATION

### Header Buttons (no change in position, updated function links)

| Button | Current | v3.0 |
|---|---|---|
| 📒 Journal | Opens Trade Journal | Opens Journal/Performance modal (combined) |
| ⚙️ Settings | Opens Settings modal | Opens Settings modal (unchanged) |
| 🌍 Geopolitical | Opens Geo modal | Opens Geo modal (unchanged) |
| 🛡️ Shield | Shows guardrail status | Unchanged |
| 📊 Correlation | Opens correlation modal | Unchanged |

---

### Column 3 — Context Intelligence Panel Specification

#### Section A: Economic Events (Next 24h)
- **Source**: Economic calendar API filtered for instrument's related currencies/assets
- **Card layout** (compact, mobile-friendly):
  - Impact level badge: 🔴 HIGH / 🟡 MEDIUM / ⚪ LOW
  - Event name + currency
  - Time (local + EST)
  - Forecast value + Previous value
- **Order**: Sorted by impact (HIGH first), then by time

#### Section B: Market Intelligence (Geopolitical + Sentiment News)
- **Source**: Existing geopolitical backend news feed
- **Card layout** (compact, mobile-friendly):
  - News source tag (NEWS SEARCH / etc.)
  - Headline (2 lines max, truncated)
  - Age (e.g. "4h ago")
  - Sentiment badge: [Bullish ●] / [Bearish ●] / [Neutral ●]
  - Impact score for the specific instrument: e.g. `Impact: +65`
- **Net Sentiment**: Aggregated score displayed at section bottom
- **Order**: Sorted by |impact score| descending

#### Section C: Top News Links *(Intelligence Viewer — redesigned)*
- Replaces embedded viewer (blocked by providers)
- Displays clickable headline list: source name + truncated headline + sentiment score
- Each item links out to the original article
- Sentiment score shown inline

---

### Column 2 — Technical Tab Specification

#### Section 1: Strategic Action & Scaling
Content moved from current SCALING tab:
- Trade action headline (Wait and Observe / Buy / Sell)
- Key zones context text
- Entry range / Stop / Target cards (3-card row)
- Visual R/R Diagram
- R/R Ratio, Probability, EV, Account Risk stats
- Fixed Scaling Entries (50/30/20 allocation cards)
- Lot size, risk, trailing stop inputs
- Log Trade + Open Chart buttons

#### Section 2: Pivot Matrix & Extensions
Content moved from current GEOPOLITICAL tab bottom section:
- R3, R2, R1 resistance levels
- Pivot (P) price
- S1, S2, S3 support levels
- 52-week Low and High

#### Section 3: AI Trade Reasoning *(new section)*
- **Header**: "WHY [BULLISH/BEARISH/NEUTRAL]" (dynamic, matches signal)
- **Bullish Factors** (bulleted, each with plain English explanation):
  - Indicator reading + what it means for this trade
  - e.g. "ADX=38.1 — Ultra-strong trend confirmed, momentum locked"
- **Bearish / Caution Factors** (bulleted):
  - e.g. "RSI=45 — Neutral, no oversold confirmation yet"
- **Next Range Estimate**:
  - UP scenario: target levels + trigger condition
  - DOWN scenario: target levels + trigger condition
- **Data Transparency Line**: Lists all indicators used (ADX, RSI, MACD, Pivot, etc.)

#### Section 4: Technical Analysis (existing, unchanged)
- Expert Battle Plan
- Macro Regime
- Technical Heat (ADX/RSI interpretation with trade impact)
- Economic Data section (instrument-specific upcoming data) *(may be redundant with Column 3 Section A — to review)*

---

### Column 2 — Risk Tab Specification

#### Layout: Two columns, side by side
```
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│  VALIDATION & RISK INTEL        │  │  PULLBACK & TRAP ANALYSIS       │
│  (existing content)             │  │  (existing content)             │
└─────────────────────────────────┘  └─────────────────────────────────┘
```
- Both cards take 50% width of tab content area
- On tablet: stacked (full width each)
- On mobile: stacked (full width each)

Below the two cards (full width):
- Probability Depth (Backtest) chart — unchanged

---

## 🗑️ TABS REMOVED (and where content goes)

| Removed Tab | Content Destination |
|---|---|
| GEOPOLITICAL | Column 3 — Market Intelligence section |
| SCALING | Column 2 — Technical Tab Section 1 (first section) |
| PERFORMANCE | Header 📒 Journal button → Performance modal |
| SETTINGS | Header ⚙️ Settings button → Settings modal |

---

## ✅ NEW TAB STRUCTURE

| Tab | Content |
|---|---|
| **TECHNICAL** | Section 1: Scaling (Strategic Action, R/R, Fixed Entries) → Section 2: Pivot Matrix → Section 3: AI Trade Reasoning → Section 4: Technical Analysis |
| **RISK** | Validation & Risk Intel (left) + Pullback & Trap Analysis (right) side-by-side → Probability Depth chart |

---

## 📐 RESPONSIVE BEHAVIOUR SUMMARY

| Viewport | Column 3 | Tab Layout | Risk Cards |
|---|---|---|---|
| Desktop (≥1025px) | Always visible, 280px wide | Full tab content visible | Side by side (50%/50%) |
| Tablet (768–1024px) | Collapsed accordion below main content, expandable | Scrollable full width | Stacked full width |
| Mobile (<768px) | Dedicated **[📅 Context]** tab in mobile nav bar | Single column scrollable | Stacked full width |

---

## ✅ CONFIRMED DECISIONS

| # | Question | Decision |
|---|---|---|
| 1 | Economic Data in Technical Tab | **Removed** — Column 3 Section A is the canonical place for economic events |
| 2 | SCALING tab | **Removed entirely** — content lives in Technical Tab Section 1 only |
| 3 | Intelligence Viewer | **Convert to Top News Links list** — clickable headlines with source + sentiment; embedded viewer dropped since blocked by providers |
| 4 | Mobile Column 3 | **Dedicated `[📅 Context]` tab** in mobile bottom navigation bar |

---

*Document status: ✅ CONFIRMED v3.0 — Implementation approved.*
