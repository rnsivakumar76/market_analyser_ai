import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TrendAnalysis {
  direction: 'bullish' | 'bearish' | 'neutral';
  fast_ma: number;
  slow_ma: number;
  price_above_fast_ma: boolean;
  price_above_slow_ma: boolean;
  description: string;
}

export interface PullbackAnalysis {
  detected: boolean;
  pullback_percent: number;
  near_support: boolean;
  support_level: number | null;
  description: string;
}

export interface StrengthAnalysis {
  signal: 'bullish' | 'bearish' | 'neutral';
  rsi: number;
  volume_ratio: number;
  adx: number;
  price_change_percent: number;
  description: string;
}

export interface PhaseAnalysis {
  phase: 'accumulation' | 'markup' | 'distribution' | 'markdown' | 'liquidation' | 'consolidation';
  score: number;
  description: string;
}

export interface PivotPoints {
  pivot: number;
  r1: number;
  r2: number;
  r3: number;
  s1: number;
  s2: number;
  s3: number;
}

export interface FibonacciLevels {
  trend: 'up' | 'down' | 'flat';
  swing_high: number;
  swing_low: number;
  ret_382: number;
  ret_500: number;
  ret_618: number;
  ext_1272: number;
  ext_1618: number;
}

export interface TechnicalAnalysis {
  pivot_points: PivotPoints;
  fibonacci: FibonacciLevels;
  least_resistance_line: 'up' | 'down' | 'flat';
  trend_breakout: 'bullish_breakout' | 'bearish_breakout' | 'none';
  breakout_confidence: number;
  description: string;
}

export interface TradeSignal {
  recommendation: 'bullish' | 'bearish' | 'neutral';
  score: number;
  reasons: string[];
  trade_worthy: boolean;
  action_plan: string;
  action_plan_details: string;
  psychological_guard: string;
  pyramiding_plan: string;
}

export interface VolatilityAnalysis {
  atr: number;
  stop_loss: number;
  take_profit: number;
  risk_reward_ratio: number;
  description: string;
}

export interface FundamentalsAnalysis {
  has_high_impact_events: boolean;
  events: string[];
  description: string;
}

export interface BacktestAnalysis {
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  description: string;
}

export interface StrategySettings {
  conviction_threshold: number;
  adx_threshold: number;
  atr_multiplier_tp: number;
  atr_multiplier_sl: number;
  portfolio_value: number;
  risk_per_trade_percent: number;
}

export interface CandleAnalysis {
  pattern: string;
  description: string;
  is_bullish: boolean | null;
}

export interface PositionSizing {
  suggested_units: number;
  risk_amount: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  correlation_penalty: number;
  final_risk_percent: number;
  description: string;
}

export interface NewsItem {
  title: string;
  source: string;
  url: string;
  sentiment_score: number;
  sentiment_label: string;
}

export interface NewsSentiment {
  score: number;
  label: string;
  sentiment_summary: string;
  news_items: NewsItem[];
}

export interface ChartData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PullbackWarningAnalysis {
  warning_score: number;
  is_warning: boolean;
  reasons: string[];
  description: string;
}

export interface InstrumentAnalysis {
  symbol: string;
  name: string;
  current_price: number;
  analysis_date: string;
  last_updated: string;
  monthly_trend: TrendAnalysis;
  weekly_pullback: PullbackAnalysis;
  daily_strength: StrengthAnalysis;
  market_phase: PhaseAnalysis;
  volatility_risk: VolatilityAnalysis;
  fundamentals: FundamentalsAnalysis;
  backtest_results: BacktestAnalysis;
  candle_patterns: CandleAnalysis;
  benchmark_direction: 'bullish' | 'bearish' | 'neutral';
  trade_signal: TradeSignal;
  technical_indicators?: TechnicalAnalysis;
  position_sizing?: PositionSizing;
  news_sentiment?: NewsSentiment;
  pullback_warning?: PullbackWarningAnalysis;
}

export interface WeeklyPerformance {
  total_pnl_percent: number;
  total_trades: number;
  win_rate: number;
  best_trade_symbol: string;
  best_trade_pnl: number;
  worst_trade_symbol: string;
  worst_trade_pnl: number;
  description: string;
}

export interface CorrelationData {
  labels: string[];
  matrix: number[][];
}

export interface AnalysisResponse {
  analysis_timestamp: string;
  instruments: InstrumentAnalysis[];
  weekly_performance: WeeklyPerformance;
  correlation_data: CorrelationData;
}

@Injectable({
  providedIn: 'root'
})
export class MarketAnalyzerService {
  private http = inject(HttpClient);
  private apiUrl = 'https://o9dgs1ujz1.execute-api.ap-southeast-1.amazonaws.com/api';

  analyzeAll(): Observable<AnalysisResponse> {
    return this.http.get<AnalysisResponse>(`${this.apiUrl}/analyze`);
  }

  analyzeSingle(symbol: string): Observable<InstrumentAnalysis> {
    return this.http.get<InstrumentAnalysis>(`${this.apiUrl}/analyze/${symbol}`);
  }

  getInstruments(): Observable<{ instruments: { symbol: string; name: string }[] }> {
    return this.http.get<{ instruments: { symbol: string; name: string }[] }>(`${this.apiUrl}/instruments`);
  }

  getChartData(symbol: string): Observable<ChartData[]> {
    return this.http.get<ChartData[]>(`${this.apiUrl}/chart/${symbol}`);
  }

  addInstrument(symbol: string, name: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/instruments`, { symbol, name });
  }

  deleteInstrument(symbol: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/instruments/${symbol}`);
  }

  getSettings(): Observable<StrategySettings> {
    return this.http.get<StrategySettings>(`${this.apiUrl}/settings`);
  }

  updateSettings(settings: StrategySettings): Observable<any> {
    return this.http.post(`${this.apiUrl}/settings`, settings);
  }
}
