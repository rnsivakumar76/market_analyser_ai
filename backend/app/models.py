from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import date


class Signal(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class MarketPhase(str, Enum):
    ACCUMULATION = "accumulation"  # Sideways at bottom
    MARKUP = "markup"              # Uptrend
    DISTRIBUTION = "distribution"  # Sideways at top
    MARKDOWN = "markdown"          # Downtrend
    LIQUIDATION = "liquidation"    # Sharp selloff
    CONSOLIDATION = "consolidation" # General sideways


class StrategyMode(str, Enum):
    LONG_TERM = "long_term"   # Monthly -> Weekly -> Daily
    SHORT_TERM = "short_term" # Daily -> 4Hour -> 1Hour


class SystemStatus(str, Enum):
    ACTIVE = "active"
    RESTRICTED = "restricted"


class PhaseAnalysis(BaseModel):
    phase: MarketPhase
    score: float
    description: str


class CandleAnalysis(BaseModel):
    pattern: str
    description: str
    is_bullish: Optional[bool]


class EventEntry(BaseModel):
    event: str
    time_utc: Optional[str] = None
    impact: str = "HIGH"


class FundamentalsAnalysis(BaseModel):
    has_high_impact_events: bool
    events: List[str]
    description: str
    event_timestamps: List[EventEntry] = []
    risk_reduction_active: bool = False
    recommended_position_multiplier: float = 1.0
    pre_event_caution: bool = False
    minutes_to_next_event: Optional[int] = None


class VolatilityAnalysis(BaseModel):
    atr: float
    stop_loss: float
    take_profit: float  # Final target
    take_profit_level1: Optional[float] = None  # Scale out 1
    take_profit_level2: Optional[float] = None  # Scale out 2
    risk_reward_ratio: float
    description: str
    atr_percentile_rank: float = 50.0
    atr_regime: str = "NORMAL"
    historical_volatility_14: float = 0.0
    hv_percentile: float = 50.0
    volatility_regime_label: str = "Normal"


class BacktestAnalysis(BaseModel):
    win_rate: float
    total_trades: int
    profit_factor: float
    avg_win: float
    avg_loss: float
    description: str
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    max_consecutive_losses: int = 0
    max_adverse_excursion_pct: float = 0.0
    sample_size: int = 0
    expectancy: float = 0.0


class TrendAnalysis(BaseModel):
    direction: Signal
    fast_ma: float
    slow_ma: float
    price_above_fast_ma: bool
    price_above_slow_ma: bool
    description: str


class PullbackAnalysis(BaseModel):
    detected: bool
    pullback_percent: float
    near_support: bool
    support_level: Optional[float]
    description: str


class PullbackWarningAnalysis(BaseModel):
    warning_score: int  # 0 to 6
    is_warning: bool
    reasons: List[str]
    description: str


class StrengthAnalysis(BaseModel):
    signal: Signal
    rsi: float
    volume_ratio: float
    adx: float
    vwap: Optional[float] = None
    vwap_dist_pct: Optional[float] = None
    price_change_percent: float
    description: str


class RelativeStrengthAnalysis(BaseModel):
    is_outperforming: bool
    symbol_return: float
    benchmark_return: float
    alpha: float
    label: str
    description: str


class PivotPoints(BaseModel):
    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float


class FibonacciLevels(BaseModel):
    trend: str
    swing_high: float
    swing_low: float
    ret_382: float
    ret_500: float
    ret_618: float
    ext_1272: float
    ext_1618: float


class TechnicalAnalysis(BaseModel):
    pivot_points: PivotPoints
    fibonacci: FibonacciLevels
    least_resistance_line: str  # 'up', 'down', 'flat'
    trend_breakout: str  # 'bullish_breakout', 'bearish_breakout', 'none'
    breakout_confidence: float  # 0 to 1
    rsi_divergence: Optional[str] = None  # 'bullish', 'bearish', None
    std_dev_1: Optional[float] = None  # 1 sigma
    std_dev_2: Optional[float] = None  # 2 sigma
    description: str


class SessionContext(BaseModel):
    pdh: float  # Previous Day High
    pdl: float  # Previous Day Low
    london_open: Optional[float] = None
    current_session_range_pct: float
    description: str


class IntermarketContext(BaseModel):
    dxy_direction: str  # 'up', 'down', 'flat'
    dxy_change_pct: float
    us10y_direction: str  # 'up', 'down', 'flat'
    us10y_change_pct: float
    gold_implication: str  # 'bullish', 'bearish', 'neutral'
    description: str


class SignalConflict(BaseModel):
    conflict_type: str  # "adx_direction_mismatch" | "mtf_disagreement" | "none"
    severity: str  # "high" | "medium" | "none"
    headline: str
    guidance: str
    trigger_price_up: Optional[float] = None
    trigger_price_down: Optional[float] = None


class InstrumentCorrelations(BaseModel):
    vs_dxy: Optional[float] = None
    vs_spx: Optional[float] = None
    vs_btc: Optional[float] = None
    period_days: int = 30
    interpretation: str = ""


class TradeSignal(BaseModel):
    recommendation: Signal
    score: int  # -100 to +100
    reasons: List[str]
    trade_worthy: bool
    action_plan: str = ""
    action_plan_details: str = ""
    psychological_guard: str = ""
    pyramiding_plan: str = ""
    scaling_plan: str = ""
    executive_summary: str = ""
    signal_conflict: Optional['SignalConflict'] = None


class PositionSizing(BaseModel):
    suggested_units: float
    risk_amount: float
    entry_price: float
    stop_loss: float
    take_profit: float
    correlation_penalty: float
    final_risk_percent: float
    description: str


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    sentiment_score: float # -1 to 1
    sentiment_label: str # Bullish, Bearish, Neutral
    published_at: Optional[str] = None # ISO-8601 or RFC-822 timestamp


class NewsSentiment(BaseModel):
    score: float # -1 to 1
    label: str # Bullish, Bearish, Neutral
    sentiment_summary: str
    news_items: List[NewsItem]


class GeoIndicatorCheck(BaseModel):
    name: str
    value: float
    status: str  # 'confirming' | 'neutral' | 'diverging'
    description: str


class GeopoliticalRisk(BaseModel):
    detected: bool
    risk_score: int  # 0–100
    risk_level: str  # 'NONE' | 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL'
    keywords_found: List[str]
    event_categories: List[str]
    expected_impact: str  # 'bullish' | 'bearish' | 'usd_bullish' | 'neutral' | 'mixed'
    impact_confidence: str  # 'HIGH' | 'MEDIUM' | 'LOW'
    indicator_confirmation: str  # 'CONFIRMED' | 'EARLY' | 'DIVERGING' | 'NONE'
    indicators: List[GeoIndicatorCheck]
    ai_narrative: str
    action_bias: str


class VolumeProfileBucket(BaseModel):
    price_low: float
    price_high: float
    volume: float
    pct_of_max: float
    is_poc: bool = False


class VolumeProfile(BaseModel):
    poc: float
    vah: float
    val: float
    num_buckets: int
    buckets: List[VolumeProfileBucket] = []
    interpretation: str = ""


class SessionVWAP(BaseModel):
    vwap: float
    upper_band: float
    lower_band: float
    distance_pct: float
    position: str
    bar_count: int
    interpretation: str = ""


class LiquidityLevel(BaseModel):
    price: float
    distance_pct: float
    level_type: str
    strength: str = "moderate"
    touches: int = 0


class LiquidityMap(BaseModel):
    resistance_levels: List[LiquidityLevel] = []
    support_levels: List[LiquidityLevel] = []
    interpretation: str = ""


class BlockFlowEvent(BaseModel):
    bar_index: int
    timestamp: str
    price: float
    volume_ratio: float
    direction: str
    body_ratio: float


class BlockFlowDetection(BaseModel):
    detected: bool
    events: List[BlockFlowEvent] = []
    net_direction: str = "neutral"
    bull_blocks: int = 0
    bear_blocks: int = 0
    interpretation: str = ""


class InstrumentAnalysis(BaseModel):
    symbol: str
    name: str
    current_price: float
    analysis_date: date
    last_updated: str
    monthly_trend: TrendAnalysis
    weekly_pullback: PullbackAnalysis
    daily_strength: StrengthAnalysis
    market_phase: PhaseAnalysis
    volatility_risk: VolatilityAnalysis
    fundamentals: FundamentalsAnalysis
    backtest_results: BacktestAnalysis
    candle_patterns: CandleAnalysis
    benchmark_direction: Signal
    trade_signal: TradeSignal
    technical_indicators: Optional[TechnicalAnalysis] = None
    position_sizing: Optional[PositionSizing] = None
    news_sentiment: Optional[NewsSentiment] = None
    pullback_warning: Optional[PullbackWarningAnalysis] = None
    relative_strength: Optional[RelativeStrengthAnalysis] = None
    expert_trade_plan: Optional[Dict[str, Any]] = None 
    strategy_mode: StrategyMode = StrategyMode.LONG_TERM
    intermarket_context: Optional['IntermarketContext'] = None
    session_context: Optional[SessionContext] = None
    instrument_correlations: Optional[InstrumentCorrelations] = None
    volume_profile: Optional[VolumeProfile] = None
    session_vwap: Optional[SessionVWAP] = None
    liquidity_map: Optional[LiquidityMap] = None
    block_flow: Optional[BlockFlowDetection] = None
    geopolitical_risk: Optional[GeopoliticalRisk] = None


class PerformanceSummary(BaseModel):
    total_pnl_percent: float
    total_trades: int
    win_rate: float
    best_trade_symbol: str
    best_trade_pnl: float
    worst_trade_symbol: str
    worst_trade_pnl: float
    description: str


class CorrelationData(BaseModel):
    labels: List[str]
    matrix: List[List[float]]


class PsychologicalGuardrail(BaseModel):
    status: SystemStatus
    daily_pnl: float
    daily_loss_limit: float
    consecutive_losses: int
    max_consecutive_losses: int
    lockdown_reason: str
    message: str


class AnalysisResponse(BaseModel):
    analysis_timestamp: str
    instruments: List[InstrumentAnalysis]
    weekly_performance: Optional[PerformanceSummary] = None
    correlation_data: Optional[CorrelationData] = None
    psychological_guardrail: Optional[PsychologicalGuardrail] = None
    is_stale: bool = False
    served_from_cache: bool = False
    data_age_minutes: Optional[int] = None


class InstrumentConfig(BaseModel):
    symbol: str
    name: str


class StrategySettings(BaseModel):
    conviction_threshold: int
    adx_threshold: int
    atr_multiplier_tp: float
    atr_multiplier_sl: float
    portfolio_value: float
    risk_per_trade_percent: float


