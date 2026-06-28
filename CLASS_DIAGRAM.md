# Market Analyser AI — Class Diagram

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  BROWSER (Angular 17 SPA)          │  AWS LAMBDA (FastAPI Backend)          │
│                                    │                                         │
│  App → Components → Services  ──── REST API ───▶  Analyzers → Models        │
│                                    │                     ▼                   │
│                                    │              TwelveData / yFinance       │
│                                    │              DynamoDB / S3               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Backend Domain Models (`backend/app/models.py`)

```mermaid
classDiagram
    direction TB

    class InstrumentAnalysis {
        +str symbol
        +str name
        +float current_price
        +date analysis_date
        +str last_updated
        +TrendAnalysis monthly_trend
        +PullbackAnalysis weekly_pullback
        +StrengthAnalysis daily_strength
        +PhaseAnalysis market_phase
        +VolatilityAnalysis volatility_risk
        +FundamentalsAnalysis fundamentals
        +BacktestAnalysis backtest_results
        +CandleAnalysis candle_patterns
        +Signal benchmark_direction
        +TradeSignal trade_signal
        +StrategyMode strategy_mode
        +Optional[TechnicalAnalysis] technical_indicators
        +Optional[RelativeStrengthAnalysis] relative_strength
        +Optional[SessionContext] session_context
        +Optional[VolumeProfile] volume_profile
        +Optional[SessionVWAP] session_vwap
        +Optional[LiquidityMap] liquidity_map
        +Optional[BlockFlowDetection] block_flow
        +Optional[GeopoliticalRisk] geopolitical_risk
        +Optional[BlowOffTopAnalysis] blowoff_top
        +Optional[PositionExitAnalysis] position_exit
        +Optional[IntermarketContext] intermarket_context
        +Optional[List~IntradaySignal~] intraday_signals
    }

    class TradeSignal {
        +Signal recommendation
        +int score
        +List~str~ reasons
        +bool trade_worthy
        +str execution_state
        +str opportunity_grade
        +str suggested_size_text
        +str action_plan
        +str executive_summary
        +Optional~SignalConflict~ signal_conflict
        +Optional~TradeVerdict~ trade_verdict
    }

    class TradeVerdict {
        +str verdict
        +str headline
        +str detail
        +str color
    }

    class SignalConflict {
        +str conflict_type
        +str severity
        +str headline
        +str guidance
        +Optional~float~ trigger_price_up
        +Optional~float~ trigger_price_down
    }

    class TrendAnalysis {
        +Signal direction
        +str description
        +float score
        +str timeframe_label
    }

    class PullbackAnalysis {
        +bool detected
        +bool near_support
        +str description
        +float score
    }

    class StrengthAnalysis {
        +Signal signal
        +float score
        +float adx
        +float rsi
        +float price_change_percent
        +Optional~float~ vwap_dist_pct
    }

    class VolatilityAnalysis {
        +str risk_level
        +float atr
        +float stop_loss
        +float take_profit
        +float atr_percentile_rank
        +str volatility_regime_label
    }

    class IntradaySignal {
        +str signal_id
        +str symbol
        +str timeframe
        +str signal_type
        +str trigger
        +float entry_price
        +float stop_loss
        +float take_profit_1
        +float take_profit_2
        +float risk_reward
        +int confidence
        +str status
        +str generated_at
        +str expires_at
    }

    class StrategyMode {
        <<enumeration>>
        LONG_TERM
        SHORT_TERM
        INTRADAY
    }

    class Signal {
        <<enumeration>>
        BULLISH
        BEARISH
        NEUTRAL
    }

    class PositionExitAnalysis {
        +bool should_exit
        +str exit_urgency
        +str exit_reason
        +str position_health
        +bool divergence_detected
        +float current_drawdown_pct
        +float recovery_probability
        +List~str~ factors
    }

    class AnalysisResponse {
        +str analysis_timestamp
        +List~InstrumentAnalysis~ instruments
        +PerformanceSummary weekly_performance
        +CorrelationData correlation_data
        +PsychologicalGuardrail psychological_guardrail
        +bool is_stale
        +bool served_from_cache
        +int data_age_minutes
    }

    InstrumentAnalysis --> TradeSignal
    InstrumentAnalysis --> TrendAnalysis
    InstrumentAnalysis --> PullbackAnalysis
    InstrumentAnalysis --> StrengthAnalysis
    InstrumentAnalysis --> VolatilityAnalysis
    InstrumentAnalysis --> PositionExitAnalysis
    InstrumentAnalysis --> IntradaySignal
    InstrumentAnalysis --> StrategyMode
    TradeSignal --> TradeVerdict
    TradeSignal --> SignalConflict
    TradeSignal --> Signal
    AnalysisResponse --> InstrumentAnalysis
```

---

## 2. Backend Analyzer Pipeline (`backend/app/analyzers/`)

```mermaid
classDiagram
    direction LR

    class analyze_instrument_lazy {
        <<function>>
        +symbol: str
        +mode: StrategyMode
        +Returns: InstrumentAnalysis
    }

    class TrendAnalyzer {
        <<module: trend_analyzer>>
        +analyze_monthly_trend(df) TrendAnalysis
    }

    class PullbackAnalyzer {
        <<module: pullback_analyzer>>
        +analyze_weekly_pullback(df) PullbackAnalysis
    }

    class StrengthAnalyzer {
        <<module: strength_analyzer>>
        +analyze_daily_strength(df) StrengthAnalysis
    }

    class VolatilityAnalyzer {
        <<module: volatility_analyzer>>
        +analyze_volatility_and_risk(df) VolatilityAnalysis
        +calculate_atr(df) float
    }

    class SignalGenerator {
        <<module: signal_generator>>
        +generate_trade_signal(...) TradeSignal
        +_detect_signal_conflict(...) SignalConflict
        +_derive_execution_profile(...) tuple
        +compute_composite_score(...) CompositeResult
        +apply_all_hard_filters(...) tuple
    }

    class IntradaySignalGenerator {
        <<module: intraday_signal_generator>>
        +detect_intraday_signals_verbose(...) List~IntradaySignal~
        +detect_ema_cross(df) signal
        +detect_macd_cross(df) signal
        +detect_confluence(df) signal
    }

    class TechnicalAnalyzer {
        <<module: technical_analyzer>>
        +analyze_technical_indicators(df) TechnicalAnalysis
        +analyze_session_context(df) SessionContext
    }

    class BacktestEngine {
        <<module: backtest_engine>>
        +get_backtest_results(sym, df) BacktestAnalysis
        +sharpe_ratio: float
        +max_drawdown_pct: float
        +expectancy: float
    }

    class PositionExitAnalyzer {
        <<module: position_exit_analyzer>>
        +analyze_position_exit(analysis) PositionExitAnalysis
    }

    class VolumeProfileAnalyzer {
        <<module: volume_profile_analyzer>>
        +analyze_volume_profile(df, mode) VolumeProfile
        +POC: float
        +VAH: float
        +VAL: float
    }

    class LiquidityMapAnalyzer {
        <<module: liquidity_map_analyzer>>
        +analyze_liquidity_map(df) LiquidityMap
        +resistance_levels: List
        +support_levels: List
    }

    class BlockFlowAnalyzer {
        <<module: block_flow_analyzer>>
        +analyze_block_flow(df) BlockFlowDetection
    }

    class DayTradingExpert {
        <<module: day_trading_expert>>
        +build_expert_trade_plan(...) Dict
        +detect_opening_range(df) ORBData
        +calculate_rvol(df) float
    }

    analyze_instrument_lazy --> TrendAnalyzer
    analyze_instrument_lazy --> PullbackAnalyzer
    analyze_instrument_lazy --> StrengthAnalyzer
    analyze_instrument_lazy --> VolatilityAnalyzer
    analyze_instrument_lazy --> SignalGenerator
    analyze_instrument_lazy --> IntradaySignalGenerator
    analyze_instrument_lazy --> TechnicalAnalyzer
    analyze_instrument_lazy --> BacktestEngine
    analyze_instrument_lazy --> PositionExitAnalyzer
    analyze_instrument_lazy --> VolumeProfileAnalyzer
    analyze_instrument_lazy --> LiquidityMapAnalyzer
    analyze_instrument_lazy --> BlockFlowAnalyzer
    analyze_instrument_lazy --> DayTradingExpert
```

---

## 3. Backend Data Layer

```mermaid
classDiagram
    direction TB

    class TwelveDataFetcher {
        +fetch_batch_data(symbols, interval, days) Dict~DataFrame~
        +fetch_batch_prices(symbols) Dict~float~
        +_rate_limit()
    }

    class DataFetcher {
        <<module: data_fetcher>>
        +fetch_historical_data(symbol, days, interval) DataFrame
    }

    class NexusDB {
        <<module: db>>
        +get_latest_analysis_results(user_id, mode, max_age) dict
        +save_analysis_results(user_id, data, mode)
        +get_instruments(user_id) List
        +is_dynamo_enabled() bool
    }

    class ConfigLoader {
        <<module: config_loader>>
        +load_config(user_id) Dict
        +get_instruments(config) List
        +get_strategy_config(config) Dict
        +ALLOWED_SYMBOLS: Set
        +DEFAULT_INSTRUMENTS: List
    }

    class run_scheduled_analysis {
        <<async function>>
        +Batches benchmark fetch (SPX, BTC, DXY, TNX)
        +Parallel instrument analysis (ThreadPoolExecutor)
        +Returns: results, perf, corr, guardrail
    }

    run_scheduled_analysis --> TwelveDataFetcher
    run_scheduled_analysis --> NexusDB
    run_scheduled_analysis --> ConfigLoader
    TwelveDataFetcher --> DataFetcher
```

---

## 4. Backend API Layer (`backend/app/main.py`)

```mermaid
classDiagram
    direction TB

    class FastAPIApp {
        <<FastAPI>>
        +GET /api/analyze → AnalysisResponse
        +GET /api/analyze/{symbol} → InstrumentAnalysis
        +GET /api/instruments
        +POST /api/instruments
        +DELETE /api/instruments/{symbol}
        +GET /api/signals
        +POST /api/signals/refresh
    }

    class AuthMiddleware {
        <<module: auth>>
        +get_current_user(token) user_id
        +verify_jwt(token) Claims
    }

    class OAuthRouter {
        <<module: oauth>>
        +GET /api/auth/login → redirect to Google
        +GET /api/auth/callback → JWT token
        +POST /api/auth/local/login
    }

    class ChatRouter {
        <<module: chat_routes>>
        +POST /api/chat → ChatResponse
        +AI Copilot: OpenAI integration
    }

    class GeopoliticalRouter {
        <<module: geopolitical_routes>>
        +GET /api/geo/sentiment → GeopoliticalResponse
        +GET /api/geo/crisis-alerts
    }

    FastAPIApp --> AuthMiddleware
    FastAPIApp --> OAuthRouter
    FastAPIApp --> ChatRouter
    FastAPIApp --> GeopoliticalRouter
    FastAPIApp --> run_scheduled_analysis
```

---

## 5. Frontend Services (`frontend/src/app/services/`)

```mermaid
classDiagram
    direction TB

    class MarketAnalyzerService {
        +analyzeAll(mode, refresh) Observable~AnalysisResponse~
        +analyzeSingle(symbol, mode) Observable~InstrumentAnalysis~
        +getInstruments() Observable
        +addInstrument(symbol, name) Observable
        +deleteInstrument(symbol) Observable
        +getChartData(symbol) Observable~ChartData[]~
        +getUserPreferences() Observable
        +saveUserPreferences(prefs) Observable
        -apiUrl: string
    }

    class AuthService {
        +isLoggedIn: boolean
        +currentUser: User
        +setToken(token)
        +setUser(user)
        +logout()
        +getGoogleAuthUrl() string
    }

    class ThemeService {
        +currentTheme: string
        +toggleTheme()
    }

    class InstrumentAnalysis_IF {
        <<interface>>
        +symbol: string
        +name: string
        +current_price: number
        +trade_signal: TradeSignal_IF
        +strategy_mode: StrategyMode
        +intraday_signals?: IntradaySignal[]
        +session_context?: SessionContext
        ... (all backend fields mirrored)
    }

    MarketAnalyzerService --> InstrumentAnalysis_IF
    MarketAnalyzerService --> AuthService
```

---

## 6. Frontend Component Tree

```mermaid
classDiagram
    direction TB

    class AppComponent {
        +instruments: Signal~InstrumentAnalysis[]~
        +strategyMode: Signal~StrategyMode~
        +selectedInstrument: Signal~InstrumentAnalysis~
        +loading: Signal~boolean~
        +runAnalysis(silent, refresh)
        +toggleStrategyMode()
        +switchStrategyMode(mode)
    }

    class InstrumentCardComponent {
        +analysis: InstrumentAnalysis
        +getExecBiasStatus() YES|NO|COUNTERTREND
        +getExecLocationStatus() YES|NO
        +getExecTriggerStatus() YES|NO
        +getExecConfirmationStatus() YES|WEAK|NO
        +getExecRiskStatus() YES|NO
        +getExecSessionStatus() YES|WEAK|NO [intraday]
        +getExecVolumeStatus() YES|NO [intraday]
        +getExecPassCount() number
        +getExecDecision() label+cssClass
        +getActiveIntradaySignals() IntradaySignal[]
        +formatPrice(v) string
    }

    class OpportunitiesOverviewComponent {
        +instruments: InstrumentAnalysis[]
        +strategyMode: string
        +filtered() InstrumentAnalysis[]
        +direction(inst) string
        +modeChange: EventEmitter
    }

    class WatchlistHeatmapComponent {
        +instruments: InstrumentAnalysis[]
        +getHeatClass(inst) string
        +getGateCount(inst) number
    }

    class OrbDashboardComponent {
        +orbInstruments: Signal~ORBPlan[]~
        +bullCount() number
        +bearCount() number
    }

    class SettingsComponent {
        +onClose: EventEmitter
        +onUpdated: EventEmitter
    }

    class StrategySettingsComponent {
        +onClose: EventEmitter
        +onUpdated: EventEmitter
    }

    class AiCopilotComponent {
        +selectedInstrument: InstrumentAnalysis
        +sendMessage(text)
    }

    class TradeJournalComponent {
        +logTrade(analysis)
    }

    class SmartAlertsComponent {
        +alerts: Alert[]
    }

    AppComponent --> InstrumentCardComponent
    AppComponent --> OpportunitiesOverviewComponent
    AppComponent --> WatchlistHeatmapComponent
    AppComponent --> OrbDashboardComponent
    AppComponent --> SettingsComponent
    AppComponent --> StrategySettingsComponent
    AppComponent --> AiCopilotComponent
    AppComponent --> TradeJournalComponent
    AppComponent --> SmartAlertsComponent
    InstrumentCardComponent --> InstrumentChartComponent
    InstrumentCardComponent --> MultiTimeframeOverlayComponent
```

---

## 7. End-to-End Request Flow

```mermaid
sequenceDiagram
    participant UI as Angular App
    participant API as FastAPI /api/analyze
    participant Cache as DynamoDB Cache
    participant Scanner as run_scheduled_analysis
    participant Fetch as TwelveDataFetcher
    participant Analyzer as analyze_instrument_lazy
    participant SigGen as SignalGenerator

    UI->>API: GET /api/analyze?mode=intraday&refresh=true
    API->>Cache: Check cache (max_age=300s)
    Cache-->>API: MISS or refresh=true
    API->>Scanner: run_scheduled_analysis(user_id, mode)
    Scanner->>Fetch: fetch_batch_data([XAU,XAG,WTI,BTC], 1h, 60d)
    Fetch-->>Scanner: DataFrames
    par Parallel (ThreadPoolExecutor)
        Scanner->>Analyzer: analyze_instrument_lazy(XAU, ...)
        Scanner->>Analyzer: analyze_instrument_lazy(XAG, ...)
        Scanner->>Analyzer: analyze_instrument_lazy(WTI, ...)
        Scanner->>Analyzer: analyze_instrument_lazy(BTC, ...)
    end
    Analyzer->>SigGen: generate_trade_signal(trend, pullback, strength, ...)
    SigGen-->>Analyzer: TradeSignal (score, verdict, gates)
    Analyzer-->>Scanner: InstrumentAnalysis
    Scanner->>Cache: save_analysis_results(user_id, results, mode)
    Scanner-->>API: [InstrumentAnalysis x4]
    API-->>UI: AnalysisResponse {instruments, performance, guardrail}
    UI->>UI: Filter intraday signals (active only)
    UI->>UI: Sort by |score| desc
    UI->>UI: Render InstrumentCard x N
```

---

## 8. Execution Gate Logic (Intraday vs Swing)

```mermaid
flowchart TD
    A[User requests analysis] --> B{Strategy Mode?}
    B -->|LONG_TERM / SHORT_TERM| C[5 Gates]
    B -->|INTRADAY| D[7 Gates]

    C --> G1[BIAS: MTF Alignment]
    C --> G2[LOCATION: Liquidity/VWAP]
    C --> G3[TRIGGER: Pullback/Tactical]
    C --> G4[CONFIRM: ADX + RSI]
    C --> G5[RISK: R:R ≥1.8]

    D --> G1
    D --> G2
    D --> G3
    D --> G4
    D --> G5
    D --> G6[SESSION: London/NY Timing]
    D --> G7[VOLUME: Session Range ≥0.5%]

    G5 --> E{Pass Count}
    G7 --> E
    E -->|≥5 swing / ≥6 intraday| F[EXECUTE FULL SIZE]
    E -->|4 swing / 5 intraday| H[EXECUTE REDUCED SIZE]
    E -->|<4 / <5| I[SETUP VALID - GATES PENDING]
```
