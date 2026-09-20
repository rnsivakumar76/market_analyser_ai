# Market Analyzer AI — Wireframes v4.0 (Decision-Support Redesign)

**Design Date**: September 20, 2026  
**Revision**: v4.0 — Proposal before implementation  
**Status**: 🟡 PROPOSAL — Pending review

---

## 1. Design Goal

Move the interface from **data display** to **decision support**. The user should immediately understand:
- What is the current signal?
- Is it safe to act?
- What is the risk and the plan?
- Why is this happening now?

---

## 2. Page Layout (Desktop)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ NEXUS PRO  [👤 User]  [🛡️ Shield]  [📊 Correlation]  [📒 Journal]  [⚙️ Settings]  [🔄 Refresh] │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌────────────────────────────────┐  ┌─────────────────────────────────────────────────────┐   │
│  │  ZONE A — DECISION CARD    │  │  ZONE B — EXECUTION CHECKLIST                       │   │
│  │  (Signal, Direction,       │  │  (Pass/Fail gates, gate score, confidence)          │   │
│  │   Confidence, Primary CTA) │  │                                                     │   │
│  └────────────────────────────┘  └─────────────────────────────────────────────────────┘   │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  ZONE C — TRADE LEVELS (only if exec pass count >= 3)                               │   │
│  │  Entry Range | Stop Loss | Target Profit                                            │   │
│  └─────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────────────────┌─────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  ZONE D — BATTLE PLAN / EXPERT ACTION                                               │   │
│  └─�─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐   │
│  │  ZONE E — ACCORDION DRAWERS                                                         │   │
│  │  ▶ Signal & Action  ▶ Risk Factors  ▶ Performance                                   │   │
│  └─────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                             │
│  ┌────────────────────────────┐  ┌────────────────────────────┐  ┌──────────────────────┐ │
│  │  ZONE F — WATCHLIST        │  │  ZONE G — PYRAMID PANEL    │  │  ZONE H — CONTEXT    │ │
│  │  Heatmap / Gate badges     │  │  (if active)               │  │  Intel / Correlation │ │
│  └────────────────────────────┘  └────────────────────────────┘  └──────────────────────┘ │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Zone Details

### ZONE A — Decision Card
- **Symbol + Name** in large type
- **Direction badge** (LONG / SHORT) with color
- **Confidence %** with gauge or progress bar
- **Primary CTA**: "Create Position" (green) or "Avoid" (gray) depending on pass count
- **Signal age / last updated** time

### ZONE B — Execution Checklist
- 5 execution gates shown as horizontal row of chips
- Each chip: icon + label + pass/fail color
- Gate score: "4/5 gates passed"
- Warning message if below threshold

### ZONE C — Trade Levels
- Hidden unless `getExecPassCount() >= 3`
- Entry range with green band
- Stop loss in red
- Target profit in green
- Risk / Reward ratio badge

### ZONE D — Expert Battle Plan
- One-sentence action: "Wait for pullback to entry range"
- Pyramid / scale instructions if applicable
- Timeframe context: swing or day

### ZONE E — Accordion Drawers
- **Signal & Action**: 4-cell MTF context row (Macro / Structure / Tactical / Signal)
- **Risk Factors**: list with warning count badge
- **Performance**: win rate, expectancy, recent trades

### ZONE F — Watchlist Heatmap
- Split into "Setup Ready" (>= 3 gates) and "Monitoring" (< 3 gates)
- Color-coded direction + gate badge per cell
- Search / filter bar

### ZONE G — Pyramid Panel (when active)
- Visual stepper: Base → Build 1 → Build 2 → Peak
- Current level highlighted
- Lots to add and price target per step
- Switch between swing (5 levels) and day (3 levels)

### ZONE H — Context Intelligence
- Top 3 correlated instruments
- Recent news / events snippets
- Risk concentration warning

---

## 4. Pyramid Manager Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ‹ Back to Overview    Pyramid Position Manager    [Swing] [Day]            │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Opportunities] [My Positions] [History]                                   ─├────────────────────────────────────────────────────────────────────────────│
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  OPPORTUNITIES PANEL                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  XAU / Gold USD                 [BEARISH] [SWING]                   │    │
│  │  Confidence: 71%   R/R: 3.00:1   Risk: MODERATE                     │    │
│  │  Current: $4067.36   Entry: $4030.76 - $4103.95   Stop: $4213.74   │    │
│  │  Target Profit: $3900.00 - $4020.00                                 │    │
│  │  Sources: RSI, MACD                                                 │    │
│  │  [Pyramid Stepper: 1  2  3  4  5]  [Create Position]                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  MY POSITIONS PANEL                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  XAU short @ 4051.0  Lots: 2  PnL: -$15.03                          │    │
│  │  [View Plan] [Edit] [Close]                                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  PYRAMID PLAN DETAIL                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Base: 2 lots @ 4051.0 → Stop 4197.38  (CURRENT)                    │    │
│  │  Build 1: +1 lot @ 4014.40 → Stop 4051.00  (FUTURE)                 │    │
│  │  Build 2: +1 lot @ 3977.81 → Stop 3999.77  (FUTURE)                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Mobile Layout

```
┌─────────────────────┐
│ Header + Menu       │
├─────────────────────┤
│ Decision Card       │
│ (stacked)           │
├─────────────────────┤
│ Execution Checklist │
│ (collapsible)       │
├─────────────────────┤
│ Trade Levels        │
├─────────────────────┤
│ Battle Plan         │
├─────────────────────┤
│ Accordion Drawers   │
├─────────────────────┤
│ Watchlist           │
│ (swipeable rows)    │
└─────────────────────┘
```

---

## 6. Open Questions

1. Should the three-column desktop layout be kept, or move to a single-center-column with side panels?
2. Should the Pyramid Manager be a full page or a slide-out panel?
3. Do you want a dark/light theme switch to be prominent?
4. Should the watchlist be sortable by confidence, risk/reward, or gate count?
5. Do you want real-time toast notifications for signal changes?

---

## 7. Implementation Notes

- Keep all calculations in `domain/` and `app/analyzers/`
- `app/models.py` is the single source of truth for response shapes
- `app/main.py` only orchestrates; no business math inline
- Frontend uses Angular standalone components, same as current stack
