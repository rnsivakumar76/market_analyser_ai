import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface GeopoliticalEvent {
  title: string;
  description: string;
  source: string;
  published: string;
  sentiment_score: number;
  affected_regions: string[];
  affected_sectors: string[];
  conflict_keywords: string[];
}

export interface TradingRecommendation {
  asset: string;
  action: string;
  reason: string;
  confidence: number;
  time_horizon: string;
  volatility_expectation: string;
}

export interface GeopoliticalData {
  timestamp: string;
  overall_sentiment: {
    overall_score: number;
    trend: string;
    volatility_risk: number;
    event_count: number;
    critical_count: number;
  };
  critical_events: GeopoliticalEvent[];
  high_impact_events: GeopoliticalEvent[];
  trading_recommendations: {
    energy_markets: TradingRecommendation[];
    commodities: TradingRecommendation[];
    equities: any[];
    currencies: any[];
  };
  affected_sectors: Record<string, number>;
  risk_assessment: {
    overall_risk_level: string;
    critical_event_count: number;
    high_impact_count: number;
    volatility_expectation: string;
    recommended_position_sizing: string;
  };
}

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
  vwap?: number;
  vwap_dist_pct?: number;
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
  rsi_divergence: 'bullish' | 'bearish' | null;
  std_dev_1?: number;
  std_dev_2?: number;
  description: string;
}

export interface SessionContext {
  pdh: number;
  pdl: number;
  london_open?: number;
  current_session_range_pct: number;
  description: string;
}

export interface IntermarketContext {
  dxy_direction: 'up' | 'down' | 'flat';
  dxy_change_pct: number;
  us10y_direction: 'up' | 'down' | 'flat';
  us10y_change_pct: number;
  gold_implication: 'bullish' | 'bearish' | 'neutral';
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
  scaling_plan: string;
  executive_summary: string;
  signal_conflict?: SignalConflict;
}

export interface SignalConflict {
  conflict_type: 'adx_direction_mismatch' | 'mtf_disagreement' | 'none';
  severity: 'high' | 'medium' | 'none';
  headline: string;
  guidance: string;
  trigger_price_up?: number;
  trigger_price_down?: number;
}

export interface InstrumentCorrelations {
  vs_dxy?: number;
  vs_spx?: number;
  vs_btc?: number;
  period_days: number;
  interpretation: string;
}

export interface VolatilityAnalysis {
  atr: number;
  stop_loss: number;
  take_profit: number;
  take_profit_level1?: number;
  take_profit_level2?: number;
  risk_reward_ratio: number;
  description: string;
  atr_percentile_rank: number;
  atr_regime: 'LOW' | 'NORMAL' | 'ELEVATED' | 'EXTREME';
  historical_volatility_14: number;
  hv_percentile: number;
  volatility_regime_label: string;
}

export interface EventEntry {
  event: string;
  time_utc?: string;
  impact: string;
}

export interface FundamentalsAnalysis {
  has_high_impact_events: boolean;
  events: string[];
  description: string;
  event_timestamps: EventEntry[];
  risk_reduction_active: boolean;
  recommended_position_multiplier: number;
  pre_event_caution: boolean;
  minutes_to_next_event?: number;
}

export interface BacktestAnalysis {
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  description: string;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  max_consecutive_losses: number;
  max_adverse_excursion_pct: number;
  sample_size: number;
  expectancy: number;
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
  published_at?: string;
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

export interface RelativeStrengthAnalysis {
  is_outperforming: boolean;
  symbol_return: number;
  benchmark_return: number;
  alpha: number;
  label: string;
  description: string;
}

export interface ExpertTradePlan {
  battle_plan: string;
  rvol: number;
  is_high_intent: boolean;
}

export type StrategyMode = 'long_term' | 'short_term';

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
  relative_strength?: RelativeStrengthAnalysis;
  expert_trade_plan?: ExpertTradePlan;
  strategy_mode: StrategyMode;
  intermarket_context?: IntermarketContext;
  session_context?: SessionContext;
  instrument_correlations?: InstrumentCorrelations;
  volume_profile?: VolumeProfile;
  session_vwap?: SessionVWAP;
  liquidity_map?: LiquidityMap;
  block_flow?: BlockFlowDetection;
}

export interface VolumeProfileBucket {
  price_low: number;
  price_high: number;
  volume: number;
  pct_of_max: number;
  is_poc: boolean;
}

export interface VolumeProfile {
  poc: number;
  vah: number;
  val: number;
  num_buckets: number;
  buckets: VolumeProfileBucket[];
  interpretation: string;
}

export interface SessionVWAP {
  vwap: number;
  upper_band: number;
  lower_band: number;
  distance_pct: number;
  position: string;
  bar_count: number;
  interpretation: string;
}

export interface LiquidityLevel {
  price: number;
  distance_pct: number;
  level_type: string;
  strength: string;
  touches: number;
}

export interface LiquidityMap {
  resistance_levels: LiquidityLevel[];
  support_levels: LiquidityLevel[];
  interpretation: string;
}

export interface BlockFlowEvent {
  bar_index: number;
  timestamp: string;
  price: number;
  volume_ratio: number;
  direction: string;
  body_ratio: number;
}

export interface BlockFlowDetection {
  detected: boolean;
  events: BlockFlowEvent[];
  net_direction: string;
  bull_blocks: number;
  bear_blocks: number;
  interpretation: string;
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

export interface PsychologicalGuardrail {
  status: 'active' | 'restricted';
  daily_pnl: number;
  daily_loss_limit: number;
  consecutive_losses: number;
  max_consecutive_losses: number;
  lockdown_reason: string;
  message: string;
}

export interface AnalysisResponse {
  analysis_timestamp: string;
  instruments: InstrumentAnalysis[];
  weekly_performance: WeeklyPerformance;
  correlation_data: CorrelationData;
  psychological_guardrail: PsychologicalGuardrail;
}

export interface NotificationPrefs {
  enabled: boolean;
  trade_worthy_alerts: boolean;
  pullback_warnings: boolean;
  score_threshold: number;
}

export interface UserPreferences {
  theme: 'dark' | 'light';
  view_mode: 'heatmap' | 'list';
  strategy_mode: StrategyMode;
  auto_refresh: boolean;
  refresh_interval: number;
  show_news: boolean;
  show_copilot: boolean;
  notifications: NotificationPrefs;
  strategy: StrategySettings;
}

@Injectable({
  providedIn: 'root'
})
export class MarketAnalyzerService {
  private http = inject(HttpClient);
  private apiUrl = environment.apiUrl;

  analyzeAll(mode: StrategyMode = 'long_term', refresh: boolean = false): Observable<AnalysisResponse> {
    const refreshParam = refresh ? '&refresh=true' : '';
    return this.http.get<AnalysisResponse>(`${this.apiUrl}/analyze?mode=${mode}${refreshParam}`);
  }

  analyzeSingle(symbol: string, mode: StrategyMode = 'long_term'): Observable<InstrumentAnalysis> {
    return this.http.get<InstrumentAnalysis>(`${this.apiUrl}/analyze/${symbol}?mode=${mode}`);
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

  // ─── Preferences API ───────────────────────────────────

  getPreferences(): Observable<UserPreferences> {
    return this.http.get<UserPreferences>(`${this.apiUrl}/preferences`);
  }

  updatePreferences(prefs: Partial<UserPreferences>): Observable<any> {
    return this.http.put(`${this.apiUrl}/preferences`, prefs);
  }

  // ─── Trade Journal ─────────────────────────────────────

  getJournal(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/journal`);
  }

  addTrade(trade: any): Observable<any> {
    return this.http.post(`${this.apiUrl}/journal`, trade);
  }

  deleteTrade(tradeId: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/journal/${tradeId}`);
  }

  // Geopolitical Analysis Methods
  getGeopoliticalSentiment(): Observable<GeopoliticalData> {
    return this.http.get<GeopoliticalData>(`${this.apiUrl}/geopolitical/sentiment`);
  }

  getCrisisAlerts(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/geopolitical/crisis-alerts`);
  }

  getEnergyMarketsAnalysis(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/geopolitical/energy-markets`);
  }

  getSafeHavenAnalysis(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/geopolitical/safe-haven`);
  }

  getCustomGeopoliticalAnalysis(regions: string[], sectors: string[]): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/geopolitical/custom-analysis`, {
      regions,
      sectors,
      time_horizon: '24h'
    });
  }

  getHistoricalSentiment(days: number = 7): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/geopolitical/historical-sentiment?days=${days}`);
  }
}
