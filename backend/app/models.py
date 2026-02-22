from pydantic import BaseModel
from typing import Optional, List
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


class PhaseAnalysis(BaseModel):
    phase: MarketPhase
    score: float
    description: str


class CandleAnalysis(BaseModel):
    pattern: str
    description: str
    is_bullish: Optional[bool]


class FundamentalsAnalysis(BaseModel):
    has_high_impact_events: bool
    events: List[str]
    description: str


class VolatilityAnalysis(BaseModel):
    atr: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    description: str


class BacktestAnalysis(BaseModel):
    win_rate: float
    total_trades: int
    profit_factor: float
    avg_win: float
    avg_loss: float
    description: str


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


class StrengthAnalysis(BaseModel):
    signal: Signal
    rsi: float
    volume_ratio: float
    adx: float
    price_change_percent: float
    description: str


class TradeSignal(BaseModel):
    recommendation: Signal
    score: int  # -100 to +100
    reasons: List[str]
    trade_worthy: bool


class PositionSizing(BaseModel):
    suggested_units: float
    risk_amount: float
    entry_price: float
    stop_loss: float
    take_profit: float
    correlation_penalty: float
    final_risk_percent: float
    description: str


class InstrumentAnalysis(BaseModel):
    symbol: str
    name: str
    current_price: float
    analysis_date: date
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
    position_sizing: Optional[PositionSizing] = None


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


class AnalysisResponse(BaseModel):
    analysis_timestamp: str
    instruments: List[InstrumentAnalysis]
    weekly_performance: PerformanceSummary
    correlation_data: CorrelationData


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


