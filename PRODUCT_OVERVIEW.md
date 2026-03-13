# Nexus Pro — Market Analyser AI
## Product Overview & Objectives

**Document Date:** March 2026  
**Version:** 3.0  
**Status:** Production Deployment

---

## 1. Introduction

**Nexus Pro** is a self-built, full-stack trading intelligence platform designed to give retail traders access to institutional-grade market analysis in a single unified dashboard. It combines technical analysis, AI-driven reasoning, geopolitical news intelligence, and quantitative risk metrics — all automated and presented in a structured decision-making interface.

The platform bridges the gap between basic consumer-grade tools (Yahoo Finance, TradingView) and expensive institutional terminals such as Bloomberg Terminal (USD $2,000+/month), delivering professional-level analysis at an accessible price point for retail and active traders.

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 17 (TypeScript) |
| Backend | Python FastAPI |
| Infrastructure | AWS Lambda, CloudFront, S3 |
| Authentication | Google OAuth 2.0 |
| Deployment | GitHub Actions CI/CD Pipeline |
| Containerisation | Docker / Docker Compose |

---

## 2. What the Platform Offers

### 2.1 Core Analysis Engine

#### Multi-Timeframe Alignment
The system simultaneously analyses four timeframes — Monthly (Primary Trend), Weekly (Structure Phase), Daily (Intermediate State), and Intraday (Tactical Momentum) — and presents a unified alignment verdict. When timeframes conflict, the system flags the disagreement with a severity rating of LOW, MEDIUM, or HIGH, alerting the trader to reduce position size or wait for cleaner alignment.

#### AI Executive Summary
A natural language recommendation (WAIT / ENTER LONG / ENTER SHORT / EXIT) is generated from the combined indicator set. Each recommendation is supported by colour-coded reasoning tags:

- **Green** — Positive / bullish factors
- **Red** — Negative / bearish factors
- **Yellow** — Neutral or conflicting signals
- **Blue** — Informational context (indicator values, data points)

#### AI Trade Reasoning
A structured breakdown of bullish versus bearish factors with supporting indicator evidence (ADX, RSI, MACD, pivot levels) and next-range scenario projections for both upside and downside cases.

---

### 2.2 Trade Setup & Execution Tools

#### Strategic Action & Scaling
- Entry range, stop loss, and target price displayed in a three-card layout
- Visual Risk/Reward diagram showing profit and loss zones
- R/R ratio, win probability, expected value, and account risk percentage calculated automatically

#### Fixed Scaling Entries (50 / 30 / 20 Allocation)
Three scaling levels based on capital allocation:
- **50% — Tactical Entry**: Primary entry at the highest-probability zone
- **30% — Base Profit Target**: Intermediate take-profit level
- **20% — Infinite Run**: Trail stop for maximum trend capture

#### Pivot Matrix
Daily pivot levels (S3 through R3) calculated from the prior session, plus 52-week high and low reference ranges, always visible as a price context grid.

#### Smart Position Sizing
- ATR-based stop loss suggestions
- Lot size calculation from account risk percentage
- Trailing stop inputs
- Log Trade and Open Chart shortcut buttons

---

### 2.3 Institutional-Grade Analytics

Nine advanced analytical modules have been implemented, features typically found only in institutional trading platforms:

| # | Feature | What It Provides |
|---|---|---|
| 1 | **Signal Conflict Resolution** | Detects opposing signals across timeframes; displays conflict severity |
| 2 | **ATR Percentile Rank & Volatility Regime** | Labels current volatility context: Quiet / Normal / Elevated / Extreme |
| 3 | **Live Correlation Coefficients** | Per-instrument correlation vs. DXY, SPX, and BTC benchmarks |
| 4 | **MAE + Backtest Quality** | Sharpe ratio, max drawdown, max consecutive losses, expectancy, sample size |
| 5 | **Economic Calendar Pre-Event Triggers** | ≤60 min to event → 50% position size cap; ≤24h → 75% cap with alert banner |
| 6 | **Volume Profile** | Point of Control (POC), Value Area High (VAH), Value Area Low (VAL) with horizontal sparklines |
| 7 | **Session VWAP** | Asia, London, and New York session VWAPs with ±1σ bands and distance percentage |
| 8 | **Liquidity Map** | Swing high/low clusters and round-number levels displayed as a resistance/support grid |
| 9 | **Block Flow Detector** | Identifies institutional-size bars (2.5× average volume + ATR body size filter) with net direction |

---

### 2.4 Risk Intelligence

#### Validation & Risk Intel
A multi-factor risk checklist covering:
- Trend structure (phase and quality)
- Momentum via ADX value and regime
- Volatility risk (ATR percentile-based)
- Volume analysis and institutional activity
- Key level position relative to pivot
- Market correlation to benchmarks

#### Pullback & Trap Analysis
Designed to warn traders of potential bear traps and false breakouts. Displays:
- Risk level: HIGH / MODERATE / LOW
- Current position context: Near Stop / Mid-Range / Near Target / Near Resistance
- Recommended action: Hold Position / Wait for Entry / Exit
- Specific warning tags (e.g. RSI divergence, volume drying up, resistance overhead)

#### Probability Depth (Backtest)
Displays win rate, profit factor, and an equity curve sparkline derived from historical backtesting of the current signal type.

---

### 2.5 Market Context Intelligence (Column 3)

A dedicated intelligence panel provides macro context for the selected instrument:

#### Economic Events — Next 24 Hours
- Filtered for currencies and assets related to the active instrument
- Cards display: impact level (🔴 HIGH / 🟡 MEDIUM / ⚪ LOW), event name, scheduled time, forecast, and previous value
- Sorted by impact level, then by time

#### Market Intelligence (News & Geopolitical Sentiment)
- Real-time news headlines with per-headline sentiment scoring
- Sentiment badge: Bullish / Bearish / Neutral
- Impact score calculated per instrument
- Net sentiment aggregate displayed at section bottom
- 5-minute refresh cycle

#### Intelligence Viewer
- Clickable top news article links with inline sentiment scores
- Replaces blocked embedded news viewers with direct outbound links

---

### 2.6 Platform Features

| Feature | Description |
|---|---|
| **Watchlist Heatmap** | Visual overview of all instruments: % price change, signal direction, trade-worthy count |
| **Trade Journal** | Log trade entries directly from within the dashboard |
| **Dark / Light Theme** | System preference detection, localStorage persistence, smooth CSS variable transitions |
| **User Manual** | In-app help with full trading terminology guide (25+ concepts explained) |
| **Google OAuth Login** | Secure authentication via Google, routed through CloudFront to AWS Lambda backend |
| **Responsive Design** | Full support for desktop (1920×1080), tablet (1024×768), and mobile (375×667) |

---

## 3. Objectives

### 3.1 Primary Objective

> **Build a professional-grade, self-contained trading decision support tool that makes institutional-quality analysis accessible to retail and active traders — without the cost and complexity of Bloomberg Terminal or Refinitiv Eikon.**

---

### 3.2 Specific Goals

#### Goal 1 — Automate Multi-Timeframe Analysis
Eliminate the need to manually read and reconcile charts across four timeframes. The system surfaces alignment status, conflicts, and contextual warnings automatically, reducing the time from data to decision.

#### Goal 2 — Reduce Emotional and Impulsive Trading
The structured AI Executive Summary and reasoning framework enforce a disciplined evaluation process before entering any trade. Every recommendation includes the "why" — not just the "what."

#### Goal 3 — Quantify Risk on Every Trade
Every setup automatically calculates R/R ratio, probability, expected value, account risk percentage, and position size. Risk is never an afterthought; it is the first output the trader sees.

#### Goal 4 — Integrate Technical + Fundamental + Geopolitical Context
No other retail tool combines technical indicators, news sentiment, geopolitical risk analysis, and economic calendar events in a single instrument-specific view. Nexus Pro presents all relevant context simultaneously.

#### Goal 5 — Deliver Institutional Features at Retail Scale
Volume Profile, Session VWAP, Block Flow Detection, Correlation Coefficients, and Backtest Quality Metrics are features normally locked behind institutional tooling. This platform makes them available in a self-hosted, affordable environment.

#### Goal 6 — Build Production-Grade Infrastructure
Full CI/CD pipeline, AWS serverless architecture, CloudFront CDN, Docker containerisation, and end-to-end tests via Playwright. This is a production-quality system, not a prototype or proof-of-concept.

#### Goal 7 — Create a Foundation for Professional Trading Use
The platform is architected for expansion. Planned enhancements include ML-based signal quality improvements, multi-asset execution integration, and institutional feature parity across additional asset classes.

---

### 3.3 Phased Development Roadmap

#### Phase 1 — Foundation (Completed)
- Multi-timeframe analysis engine
- Trade signal generation and scoring
- AI Executive Summary with reasoning
- Geopolitical news sentiment
- Risk validation checklist
- Google OAuth authentication
- AWS serverless deployment

#### Phase 2 — Institutional Features (Completed)
- Signal conflict detection
- ATR percentile rank and volatility regime
- Live correlation coefficients
- MAE and backtest quality metrics
- Economic calendar pre-event triggers
- Volume Profile, Session VWAP, Liquidity Map, Block Flow Detector
- Dark/light theme system
- Trading terminology user manual

#### Phase 3 — Professional Enhancement (In Progress / Planned)
- Machine learning-based signal quality models
- Historical event-to-price correlation analysis
- Multi-asset coverage expansion (equities, forex, fixed income)
- Advanced VaR and stress testing
- Brokerage API integration for trade execution
- Performance attribution and advanced analytics

---

## 4. Competitive Positioning

| Platform | Cost | Geopolitical Intel | Technical Analysis | Retail Focus |
|---|---|---|---|---|
| Bloomberg Terminal | USD $2,000+/month | ✅ Comprehensive | ✅ Full | ❌ Enterprise |
| Refinitiv Eikon | USD $1,500+/month | ✅ Comprehensive | ✅ Full | ❌ Enterprise |
| TradingView Pro | USD $30–60/month | ❌ Basic | ✅ Community-driven | ✅ Yes |
| Yahoo Finance | Free | ❌ None | ❌ Basic | ✅ Yes |
| **Nexus Pro** | **Self-hosted** | **✅ Integrated** | **✅ Multi-factor** | **✅ Yes** |

**Key Differentiator**: Nexus Pro is the only retail-focused platform that integrates live geopolitical sentiment, economic calendar triggers, institutional-grade volume and flow analytics, and multi-timeframe AI reasoning in a single instrument-specific dashboard.

---

## 5. Target User

| User Type | Use Case |
|---|---|
| **Retail Trader** | Professional analysis tools without institutional cost |
| **Active Trader** | Real-time event-driven trade setups and risk management |
| **Portfolio Manager** | Macro risk context for position management |
| **Trading Educator** | Structured framework for teaching market dynamics |

---

## 6. Summary

Nexus Pro represents a serious, self-directed engineering and trading research project — one that has evolved from a basic multi-timeframe screener into a comprehensive trading intelligence platform with nine institutional-grade features, a full AWS serverless deployment, CI/CD automation, and a professional UI designed to v3.0 wireframe specifications.

The platform is live, deployed, and continues to receive regular feature enhancements across both the backend analysis engine and the Angular frontend — with every change tested, committed, and deployed via an automated pipeline.

---

*Document prepared: March 2026*  
*Platform: Nexus Pro — Market Analyser AI*  
*Repository: market_analyser_ai (private)*
