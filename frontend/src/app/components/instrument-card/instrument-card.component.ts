import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis, MarketAnalyzerService, ChartData, NewsItem } from '../../services/market-analyzer.service';
import { InstrumentChartComponent } from '../instrument-chart/instrument-chart.component';

@Component({
  selector: 'app-instrument-card',
  standalone: true,
  imports: [CommonModule, InstrumentChartComponent],
  template: `
    <div class="card" [class]="getCardClass()">
      <div class="card-header">
        <div class="symbol-info">
          <div class="symbol-row">
            <span class="symbol">{{ analysis.symbol }}</span>
            @if (analysis.benchmark_direction === 'bullish') {
              <span class="beta-status good" title="Market Beta: Major market index is bullish. Trend is supporting your trades.">🚀 Beta OK</span>
            } @else if (analysis.benchmark_direction === 'bearish') {
              <span class="beta-status bad" title="Market Beta: Major market index is bearish. High risk of failure for buy setups.">⚠️ Beta Risk</span>
            }
            @if (analysis.relative_strength) {
              <span class="alpha-status" [class]="getAlphaClass()" [title]="analysis.relative_strength.description">
                {{ analysis.relative_strength.label === 'Leader' ? '🌟' : '📊' }} Alpha: {{ analysis.relative_strength.alpha > 0 ? '+' : '' }}{{ analysis.relative_strength.alpha.toFixed(1) }}%
              </span>
            }
          </div>
          <span class="name">{{ analysis.name }}</span>
        </div>
        <div class="header-actions-right">
          <div class="price-info">
            <span class="price" title="Current or Last Daily Close Price">\${{ analysis.current_price.toFixed(2) }}</span>
            <span class="change" [class]="getPriceChangeClass()">
              {{ analysis.daily_strength.price_change_percent > 0 ? '+' : '' }}{{ analysis.daily_strength.price_change_percent.toFixed(2) }}%
            </span>
          </div>
          <div class="last-updated-row">
            <span class="last-updated-text">Updated: {{ getTimeAgo(analysis.last_updated) }}</span>
            <button class="btn-refresh-local" (click)="onRefresh()" title="Refresh Instrument">🔄</button>
          </div>
        </div>
      </div>

      <div class="card-content">
        <!-- Main Column (Left): Execution & Warnings -->
        <div class="main-column">
          <!-- 1. ACTIONABLE PLAN (PROMINENT AT TOP) -->
          <div class="action-plan" [class]="getSignalClass()">
            <div class="plan-header">Strategic Action Plan</div>
            <div class="plan-title">{{ analysis.trade_signal.action_plan }}</div>
            <p class="plan-details">{{ analysis.trade_signal.action_plan_details }}</p>

            @if (analysis.trade_signal.psychological_guard) {
              <div class="psych-guard">
                <span class="guard-icon">🛡️</span>
                <span class="guard-text"><strong>Psychological Rule:</strong> {{ analysis.trade_signal.psychological_guard }}</span>
              </div>
            }

            @if (analysis.trade_signal.pyramiding_plan && analysis.trade_signal.pyramiding_plan !== 'N/A') {
              <div class="pyramid-plan">
                <span class="pyramid-icon">🔼</span>
                <span class="pyramid-text"><strong>Pyramiding Range:</strong> {{ analysis.trade_signal.pyramiding_plan }}</span>
              </div>
            }

            @if (analysis.trade_signal.scaling_plan && analysis.trade_signal.scaling_plan !== 'N/A') {
              <div class="scaling-plan">
                <span class="scaling-icon">⚖️</span>
                <span class="scaling-text"><strong>Scaling Plan:</strong> {{ analysis.trade_signal.scaling_plan }}</span>
              </div>
            }
          </div>

          <!-- 2. PULLBACK WARNING (URGENT ALERT) -->
          @if (analysis.pullback_warning) {
            <div class="pullback-warning-section" [class.active-warning]="analysis.pullback_warning.is_warning">
              <div class="warning-header">
                <span class="warning-icon">⚠️</span>
                Pullback Risk Assessment
                <span class="warning-score" [class.risky]="analysis.pullback_warning.is_warning">
                  Score: {{ analysis.pullback_warning.warning_score }}/8
                </span>
              </div>
              <p class="description">{{ analysis.pullback_warning.description }}</p>
              @if (analysis.pullback_warning.reasons.length > 0) {
                <ul class="warning-reasons">
                  @for (reason of analysis.pullback_warning.reasons; track reason) {
                    <li>{{ reason }}</li>
                  }
                </ul>
              }
            </div>
          }

          <!-- 3. CHART INTERACTION -->
          <div class="chart-action">
            <button class="btn-chart" (click)="toggleChart()" [class.active]="showChart">
              {{ showChart ? '📊 Close Chart' : '📊 View Interactive Chart' }}
            </button>
          </div>

          @if (showChart) {
            <div class="chart-wrapper">
              @if (isLoadingChart) {
                <div class="chart-loading">Loading chart data...</div>
              } @else if (chartData.length > 0) {
                <app-instrument-chart [data]="chartData" [symbol]="analysis.symbol"></app-instrument-chart>
              } @else {
                <div class="chart-error">Failed to load chart data.</div>
              }
            </div>
          }

          <!-- 4. CORE ANALYSIS GRID -->
          <div class="analysis-grid">
            <div class="analysis-item">
              <div class="analysis-header">
                <span class="trend-badge" [class]="getTrendClass()">
                  {{ analysis.monthly_trend.direction.toUpperCase() }}
                </span>
                <span class="label">Primary Trend ({{ macroLabel }})</span>
              </div>
              <p class="description">{{ analysis.monthly_trend.description }}</p>
            </div>

            <div class="analysis-item phase-item">
              <div class="analysis-header">
                <span class="phase-badge" [class]="getPhaseClass()">
                  {{ analysis.market_phase.phase.toUpperCase() }}
                </span>
                <span class="label">Structure Phase</span>
              </div>
              <p class="description">{{ analysis.market_phase.description }}</p>
            </div>

            <div class="analysis-item">
              <div class="analysis-header">
                <span class="trend-badge" [class]="getPullbackClass()">
                  {{ analysis.weekly_pullback.detected ? 'PULLBACK' : 'EXTENDED' }}
                </span>
                <span class="label">Intermediate State ({{ pullbackLabel }})</span>
              </div>
              <p class="description">{{ analysis.weekly_pullback.description }}</p>
            </div>

            <div class="analysis-item">
              <div class="analysis-header">
                <span class="trend-badge" [class]="getStrengthClass()">
                  {{ analysis.daily_strength.signal.toUpperCase() }}
                </span>
                <span class="label">Tactical Momentum ({{ executionLabel }})</span>
              </div>
              <p class="description">{{ analysis.daily_strength.description }}</p>
            </div>
          </div>

          <!-- 5. CANDLE TRIGGERS -->
          @if (analysis.candle_patterns && analysis.candle_patterns.pattern !== 'none') {
            <div class="candle-trigger" [class.bullish]="analysis.candle_patterns.is_bullish === true" [class.bearish]="analysis.candle_patterns.is_bullish === false">
              <span class="trigger-label">Trigger Candle:</span>
              <span class="trigger-value">{{ analysis.candle_patterns.pattern.replace('_', ' ').toUpperCase() }}</span>
              <p class="trigger-desc">{{ analysis.candle_patterns.description }}</p>
            </div>
          }

          <!-- 6. NEWS INTELLIGENCE (BOTTOM OF MAIN) -->
          @if (analysis.news_sentiment && analysis.news_sentiment.news_items.length > 0) {
            <div class="news-section">
              <div class="news-header">
                News Intelligence
                <span class="news-sentiment-badge" [class]="analysis.news_sentiment.label.toLowerCase()">
                  {{ analysis.news_sentiment.label }}
                </span>
              </div>
              <p class="news-summary">{{ analysis.news_sentiment.sentiment_summary }}</p>
              <div class="news-items">
                @for (item of analysis.news_sentiment.news_items.slice(0, 3); track item.title) {
                  <div (click)="openNewsModal(item)" class="news-item-link">
                    <span class="news-item-title">{{ item.title }}</span>
                    <div class="news-item-meta">
                      <span class="news-source">{{ item.source }}</span>
                      <span class="news-sentiment" [class]="item.sentiment_label.toLowerCase()">{{ item.sentiment_label }}</span>
                    </div>
                  </div>
                }
              </div>
            </div>
          }
        </div>

        <!-- Side Column (Right): Technical Specs -->
        <div class="side-column">
          <!-- 1. SIGNAL & SCORE -->
          <div class="trade-signal">
            <div class="signal-badge" [class]="getSignalClass()">
              <span class="signal-icon">{{ getSignalIcon() }}</span>
              <span class="signal-text">{{ analysis.trade_signal.recommendation.toUpperCase() }}</span>
            </div>
            <div class="score">
              <span class="score-label">Score:</span>
              <span class="score-value" [class]="getScoreClass()">{{ analysis.trade_signal.score }}</span>
            </div>
            @if (analysis.trade_signal.trade_worthy) {
              <span class="trade-worthy">✓ Trade Worthy</span>
            }
          </div>

          <!-- 2. POSITION SIZING -->
          @if (analysis.position_sizing) {
            <div class="sizing-section">
              <div class="sizing-header">Risk-Adjusted Sizing</div>
              <div class="sizing-grid">
                <div class="sizing-item main">
                  <span class="sizing-label">Suggested Units</span>
                  <span class="sizing-value highlight">{{ analysis.position_sizing.suggested_units }}</span>
                </div>
                <div class="sizing-item">
                  <span class="sizing-label">Risk Amount</span>
                  <span class="sizing-value">\${{ analysis.position_sizing.risk_amount }}</span>
                </div>
                <div class="sizing-item">
                  <span class="sizing-label">Risk %</span>
                  <span class="sizing-value">{{ analysis.position_sizing.final_risk_percent }}%</span>
                </div>
                <div class="sizing-item">
                  <span class="sizing-label">Corr. Penalty</span>
                  <span class="sizing-value" [class.warn]="analysis.position_sizing.correlation_penalty > 0">
                    -{{ analysis.position_sizing.correlation_penalty }}%
                  </span>
                </div>
              </div>
              <p class="description sizing-desc">{{ analysis.position_sizing.description }}</p>
            </div>
          }

          <!-- 3. VOLATILITY & RISK -->
          @if (analysis.volatility_risk) {
            <div class="risk-section">
              <div class="risk-header">Risk & Volatility Management</div>
              <div class="risk-grid">
                <div class="risk-item">
                  <span class="risk-label">ATR (14D)</span>
                  <span class="risk-value">{{ analysis.volatility_risk.atr.toFixed(3) }}</span>
                </div>
                <div class="risk-item">
                  <span class="risk-label">Stop Loss</span>
                  <span class="risk-value sl">\${{ analysis.volatility_risk.stop_loss.toFixed(3) }}</span>
                </div>
                <div class="risk-item">
                  <span class="risk-label">Take Profit</span>
                  <span class="risk-value tp">\${{ analysis.volatility_risk.take_profit.toFixed(3) }}</span>
                </div>
                <div class="risk-item">
                  <span class="risk-label">RR Ratio</span>
                  <span class="risk-value">{{ analysis.volatility_risk.risk_reward_ratio.toFixed(2) }}</span>
                </div>
              </div>
              <p class="description risk-desc">{{ analysis.volatility_risk.description }}</p>
            </div>
          }

          <!-- 4. PIVOT MATRIX & BREAKOUT -->
          @if (analysis.technical_indicators) {
            <div class="tech-indicators-section">
              <div class="tech-header">Strategic Pivot Matrix</div>
              @if (analysis.technical_indicators.trend_breakout !== 'none') {
                <div class="breakout-badge" [class]="getBreakoutClass()">
                  🎯 {{ analysis.technical_indicators.trend_breakout.replace('_', ' ').toUpperCase() }} 
                  ({{ (analysis.technical_indicators.breakout_confidence * 100).toFixed(0) }}%)
                </div>
              }
              <div class="tech-grid pivot-matrix">
                <div class="tech-item"><span class="tech-label">Resistance 3</span><span class="tech-value res">\${{ analysis.technical_indicators.pivot_points.r3 }}</span></div>
                <div class="tech-item"><span class="tech-label">Resistance 2</span><span class="tech-value res">\${{ analysis.technical_indicators.pivot_points.r2 }}</span></div>
                <div class="tech-item"><span class="tech-label">Resistance 1</span><span class="tech-value res">\${{ analysis.technical_indicators.pivot_points.r1 }}</span></div>
                <div class="tech-item"><span class="tech-label">Support 1</span><span class="tech-value sup">\${{ analysis.technical_indicators.pivot_points.s1 }}</span></div>
                <div class="tech-item"><span class="tech-label">Support 2</span><span class="tech-value sup">\${{ analysis.technical_indicators.pivot_points.s2 }}</span></div>
                <div class="tech-item"><span class="tech-label">Support 3</span><span class="tech-value sup">\${{ analysis.technical_indicators.pivot_points.s3 }}</span></div>
              </div>
              
              <div class="tech-grid">
                <div class="tech-item pivot-main">
                  <span class="tech-label">Daily Pivot Point</span>
                  <span class="tech-value">\${{ analysis.technical_indicators.pivot_points.pivot }}</span>
                </div>
                <div class="tech-item">
                  <span class="tech-label">Least Resistance</span>
                  <span class="tech-value" [class]="getResistanceClass()">
                    {{ analysis.technical_indicators.least_resistance_line.toUpperCase() }}
                  </span>
                </div>
              </div>

              <!-- Swing Fibonacci Ranges -->
              <div class="tech-header fib-header">Swing Fibonacci Ranges <span class="fib-trend" [class]="analysis.technical_indicators.fibonacci.trend">({{ analysis.technical_indicators.fibonacci.trend.toUpperCase() }})</span></div>
              <div class="tech-grid fib-matrix">
                <div class="tech-item"><span class="tech-label">Ext 1.618</span><span class="tech-value ext">\${{ analysis.technical_indicators.fibonacci.ext_1618 }}</span></div>
                <div class="tech-item"><span class="tech-label">Ext 1.272</span><span class="tech-value ext">\${{ analysis.technical_indicators.fibonacci.ext_1272 }}</span></div>
                <div class="tech-item"><span class="tech-label">Swing High</span><span class="tech-value swing">\${{ analysis.technical_indicators.fibonacci.swing_high }}</span></div>
                <div class="tech-item"><span class="tech-label">Ret 38.2%</span><span class="tech-value ret">\${{ analysis.technical_indicators.fibonacci.ret_382 }}</span></div>
                <div class="tech-item"><span class="tech-label">Ret 61.8%</span><span class="tech-value ret">\${{ analysis.technical_indicators.fibonacci.ret_618 }}</span></div>
                <div class="tech-item"><span class="tech-label">Swing Low</span><span class="tech-value swing">\${{ analysis.technical_indicators.fibonacci.swing_low }}</span></div>
              </div>
              
              <p class="description tech-desc">{{ analysis.technical_indicators.description }}</p>
            </div>
          }

          <!-- 5. BACKTEST PERFORMANCE -->
          @if (analysis.backtest_results) {
            <div class="backtest-section" [class.low-confidence]="analysis.backtest_results.win_rate < 45">
              <div class="backtest-header">Strategy Probability (1Y Backtest)</div>
              <div class="backtest-stats">
                <div class="backtest-stat">
                  <span class="stat-label">Win Rate</span>
                  <span class="stat-val" [class.good]="analysis.backtest_results.win_rate >= 50">
                    {{ analysis.backtest_results.win_rate.toFixed(1) }}%
                  </span>
                </div>
                <div class="backtest-stat">
                  <span class="stat-label">Total Trades</span>
                  <span class="stat-val">{{ analysis.backtest_results.total_trades }}</span>
                </div>
                <div class="backtest-stat">
                  <span class="stat-label">Profit Factor</span>
                  <span class="stat-val">{{ analysis.backtest_results.profit_factor }}</span>
                </div>
              </div>
              <p class="description backtest-desc">{{ analysis.backtest_results.description }}</p>
            </div>
          }

          <!-- 6. FUNDAMENTAL CONTEXT -->
          @if (analysis.fundamentals) {
            <div class="fundamentals-section" [class.warning]="analysis.fundamentals.has_high_impact_events">
              <div class="fundamentals-header">Fundamental Context</div>
              <p class="description fund-desc">{{ analysis.fundamentals.description }}</p>
              @if (analysis.fundamentals.events.length > 0) {
                <ul class="fund-events">
                  @for (event of analysis.fundamentals.events; track event) {
                    <li>{{ event }}</li>
                  }
                </ul>
              }
            </div>
          }

          <!-- 7. INDICATORS & REASONS -->
          <div class="indicators">
            <div class="indicator-item">
              <span class="ind-label">RSI</span>
              <span class="ind-value">{{ analysis.daily_strength.rsi.toFixed(1) }}</span>
            </div>
            <div class="indicator-item" title="Average Directional Index - Trend Strength">
              <span class="ind-label">ADX</span>
              <span class="ind-value" [class.strong]="analysis.daily_strength.adx > 25" [class.weak]="analysis.daily_strength.adx < 20">
                {{ analysis.daily_strength.adx.toFixed(1) }}
              </span>
            </div>
            <div class="indicator-item">
              <span class="ind-label">Volume</span>
              <span class="ind-value">{{ analysis.daily_strength.volume_ratio.toFixed(2) }}x</span>
            </div>
            <div class="indicator-item">
              <span class="ind-label">20 MA</span>
              <span class="ind-value">\${{ analysis.monthly_trend.fast_ma.toFixed(2) }}</span>
            </div>
          </div>

          @if (analysis.trade_signal.reasons.length > 0) {
            <div class="reasons highlight-reasons">
              <h4>Trustworthy Signals</h4>
              <ul>
                @for (reason of analysis.trade_signal.reasons; track reason) {
                  <li>{{ reason }}</li>
                }
              </ul>
            </div>
          }
        </div>
      </div>
      
      @if (selectedNewsItem) {
        <div class="news-modal-overlay" (click)="closeNewsModal()">
          <div class="news-modal-content news-preview-card" (click)="$event.stopPropagation()">
            <div class="news-modal-header">
              <h3>Intelligence Viewer</h3>
              <button class="close-btn" (click)="closeNewsModal()">×</button>
            </div>
            <div class="news-preview-body">
              <span class="news-preview-source">{{ selectedNewsItem.source }}</span>
              <h2 class="news-preview-title">{{ selectedNewsItem.title }}</h2>
              <div class="news-preview-meta">
                <span class="news-sentiment" [class]="selectedNewsItem.sentiment_label.toLowerCase()">
                  Sentiment: {{ selectedNewsItem.sentiment_label }} (Score: {{ selectedNewsItem.sentiment_score.toFixed(2) }})
                </span>
              </div>
              <p class="news-preview-text">
                Direct embedded viewing is blocked by the news provider's security settings.
              </p>
              <a [href]="selectedNewsItem.url" target="_blank" class="btn-read-full">Read Full Article on {{ selectedNewsItem.source }} ↗</a>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .card {
      background: #1e1e2e;
      border-radius: 12px;
      padding: 20px;
      border: 1px solid #313244;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }

    .card.bullish {
      border-left: 4px solid #a6e3a1;
    }

    .card.bearish {
      border-left: 4px solid #f38ba8;
    }

    .card.neutral {
      border-left: 4px solid #f9e2af;
    }

    .card-content {
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 24px;
      align-items: start;
    }

    .analysis-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }

    .trend-badge {
      font-size: 0.65rem;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }

    .trend-badge.bullish { background: rgba(166, 227, 161, 0.15); color: #a6e3a1; border: 1px solid rgba(166, 227, 161, 0.3); }
    .trend-badge.bearish { background: rgba(243, 139, 168, 0.15); color: #f38ba8; border: 1px solid rgba(243, 139, 168, 0.3); }
    .trend-badge.neutral { background: rgba(249, 226, 175, 0.15); color: #f9e2af; border: 1px solid rgba(249, 226, 175, 0.3); }

    .label {
      font-size: 0.75rem;
      font-weight: 700;
      color: #6c7086;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .description {
      font-size: 0.9rem;
      line-height: 1.5;
      color: #cdd6f4;
      margin: 0;
    }

    .side-column {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    @media (max-width: 1000px) {
      .card-content {
        grid-template-columns: 1fr;
      }
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }

    .symbol-info {
      display: flex;
      flex-direction: column;
    }

    .header-actions-right {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 8px;
    }

    .last-updated-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .last-updated-text {
      font-size: 0.7rem;
      color: #9399b2;
      font-style: italic;
    }

    .btn-refresh-local {
      background: rgba(137, 180, 250, 0.1);
      border: 1px solid rgba(137, 180, 250, 0.2);
      border-radius: 4px;
      padding: 4px 6px;
      cursor: pointer;
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }

    .btn-refresh-local:hover {
      background: rgba(137, 180, 250, 0.3);
      transform: rotate(15deg);
    }

    .symbol-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px; /* Added margin for spacing with name */
    }

    .symbol {
      font-size: 1.5rem;
      font-weight: 700;
      color: #cdd6f4;
      margin: 0;
    }

    .beta-status {
      font-size: 0.65rem;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 700;
      text-transform: uppercase;
    }

    .beta-status.good {
      background: rgba(166, 227, 161, 0.1);
      color: #a6e3a1;
      border: 1px solid rgba(166, 227, 161, 0.2);
    }

    .beta-status.bad {
      background: rgba(243, 139, 168, 0.1);
      color: #f38ba8;
      border: 1px solid rgba(243, 139, 168, 0.2);
    }

    .alpha-status {
      font-size: 0.65rem;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 700;
      text-transform: uppercase;
      background: rgba(137, 180, 250, 0.1);
      color: #89b4fa;
      border: 1px solid rgba(137, 180, 250, 0.2);
      
      &.leader {
        background: rgba(249, 226, 175, 0.1);
        border-color: #f9e2af;
        color: #f9e2af;
        box-shadow: 0 0 10px rgba(249, 226, 175, 0.1);
      }
      
      &.laggard {
        background: rgba(243, 139, 168, 0.1);
        border-color: #f38ba8;
        color: #f38ba8;
      }
    }

    .name {
      font-size: 0.8rem; /* Changed from 0.85rem */
      color: #6c7086;
    }

    .price {
      font-size: 1.25rem;
      font-weight: 600;
      color: #cdd6f4;
    }

    .change {
      display: block;
      font-size: 0.9rem;
      text-align: right;
    }

    .change.positive { color: #a6e3a1; }
    .change.negative { color: #f38ba8; }

    .trade-signal {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 12px;
      background: #181825;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .signal-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 20px;
      font-weight: 600;
      font-size: 0.85rem;
    }

    .signal-badge.bullish {
      background: rgba(166, 227, 161, 0.2);
      color: #a6e3a1;
    }

    .signal-badge.bearish {
      background: rgba(243, 139, 168, 0.2);
      color: #f38ba8;
    }

    .signal-badge.neutral {
      background: rgba(249, 226, 175, 0.2);
      color: #f9e2af;
    }

    .signal-icon {
      font-size: 1rem;
    }

    .score {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .score-label {
      color: #6c7086;
      font-size: 0.85rem;
    }

    .score-value {
      font-weight: 700;
      font-size: 1.1rem;
    }

    .score-value.positive { color: #a6e3a1; }
    .score-value.negative { color: #f38ba8; }
    .score-value.neutral { color: #f9e2af; }

    .trade-worthy {
      margin-left: auto;
      color: #a6e3a1;
      font-weight: 600;
      font-size: 0.85rem;
    }

    .analysis-grid {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 16px;
    }

    .analysis-item {
      padding: 10px;
      background: #181825;
      border-radius: 6px;
    }

    .analysis-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }

    .indicator {
      font-size: 0.75rem;
    }

    .indicator.bullish { color: #a6e3a1; }
    .indicator.bearish { color: #f38ba8; }
    .indicator.neutral { color: #f9e2af; }

    .label {
      font-weight: 600;
      color: #cdd6f4;
      font-size: 0.9rem;
    }

    .description {
      color: #a6adc8;
      font-size: 0.8rem;
      margin: 0;
      line-height: 1.4;
    }

    .phase-badge {
      font-size: 0.65rem;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .phase-badge.markup { background: rgba(166, 227, 161, 0.2); color: #a6e3a1; border: 1px solid #a6e3a1; }
    .phase-badge.markdown { background: rgba(243, 139, 168, 0.2); color: #f38ba8; border: 1px solid #f38ba8; }
    .phase-badge.accumulation { background: rgba(203, 166, 247, 0.2); color: #cba6f7; border: 1px solid #cba6f7; }
    .phase-badge.distribution { background: rgba(250, 179, 135, 0.2); color: #fab387; border: 1px solid #fab387; }
    .phase-badge.liquidation { background: #f38ba8; color: #11111b; }
    .phase-badge.consolidation { background: rgba(137, 180, 250, 0.2); color: #89b4fa; border: 1px solid #89b4fa; }

    .phase-item {
      border: 1px solid rgba(205, 214, 244, 0.1);
      background: rgba(24, 24, 37, 0.5);
    }

    .risk-section {
      background: rgba(30, 30, 46, 0.6);
      border: 1px solid #313244;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .risk-header {
      color: #f9e2af;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .risk-header::before {
      content: "🛡️";
    }

    .risk-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 8px;
    }

    .risk-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .risk-label {
      font-size: 0.7rem;
      color: #6c7086;
    }

    .risk-value {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 0.9rem;
    }

    .risk-value.sl { color: #f38ba8; }
    .risk-value.tp { color: #a6e3a1; }

    .risk-desc {
      font-style: italic;
      color: #9399b2;
      border-top: 1px dashed #313244;
      padding-top: 8px;
      margin-top: 4px;
    }

    .fundamentals-section {
      background: rgba(30, 30, 46, 0.6);
      border: 1px solid #313244;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .fundamentals-section.warning {
      border: 1px solid #f9e2af;
      background: rgba(249, 226, 175, 0.05);
    }

    .fundamentals-header {
      color: #89b4fa;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .fundamentals-header::before {
      content: "🌐";
    }

    .fundamentals-section.warning .fundamentals-header {
      color: #f9e2af;
    }

    .fund-desc {
      font-size: 0.8rem;
      line-height: 1.4;
      margin-bottom: 8px !important;
    }

    .fund-events {
      margin: 0;
      padding-left: 18px;
      list-style-type: "⚠️";
    }

    .fund-events li {
      color: #f9e2af;
      font-size: 0.75rem;
      font-weight: 600;
      margin-bottom: 4px;
      padding-left: 6px;
    }

    .backtest-section {
      background: rgba(30, 30, 46, 0.4);
      border: 1px solid #313244;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .backtest-section.low-confidence {
      border-color: #f38ba8;
      background: rgba(243, 139, 168, 0.05);
    }

    .backtest-header {
      color: #cba6f7;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .backtest-header::before {
      content: "📈";
    }

    .backtest-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 8px;
    }

    .backtest-stat {
      display: flex;
      flex-direction: column;
    }

    .stat-label {
      font-size: 0.7rem;
      color: #6c7086;
    }

    .stat-val {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 0.9rem;
    }

    .stat-val.good { color: #a6e3a1; }

    .backtest-desc {
      font-size: 0.75rem;
      color: #a6adc8;
      border-top: 1px solid #313244;
      padding-top: 8px;
      margin-top: 4px;
      line-height: 1.4;
    }

    .indicators {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 16px;
    }

    .indicator-item {
      text-align: center;
      padding: 8px;
      background: #181825;
      border-radius: 6px;
    }

    .ind-label {
      display: block;
      font-size: 0.7rem;
      color: #6c7086;
      margin-bottom: 2px;
    }

    .ind-value {
      font-weight: 700;
      color: #cdd6f4;
    }

    .sizing-section {
      background: rgba(250, 179, 135, 0.05);
      border: 1px solid rgba(250, 179, 135, 0.2);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .sizing-header {
      color: #fab387;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .sizing-header::before {
      content: "⚖️";
    }

    .sizing-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 8px;
    }

    .sizing-item {
      display: flex;
      flex-direction: column;
    }

    .sizing-label {
      font-size: 0.7rem;
      color: #9399b2;
    }

    .sizing-value {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 0.9rem;
    }

    .sizing-value.highlight {
      color: #fab387;
      font-size: 1.1rem;
    }

    .sizing-value.warn {
      color: #f38ba8;
    }

    .sizing-desc {
      font-size: 0.75rem;
      color: #a6adc8;
      border-top: 1px solid rgba(250, 179, 135, 0.1);
      padding-top: 8px;
      margin-top: 4px;
    }

    .ind-value.strong { color: #a6e3a1; }
    .ind-value.weak { color: #6c7086; }

    .candle-trigger {
      background: rgba(203, 166, 247, 0.05);
      border: 1px dashed #cba6f7;
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 16px;
    }

    .candle-trigger.bullish {
      border-color: #a6e3a1;
      background: rgba(166, 227, 161, 0.05);
    }

    .candle-trigger.bearish {
      border-color: #f38ba8;
      background: rgba(243, 139, 168, 0.05);
    }

    .trigger-label {
      font-size: 0.7rem;
      color: #9399b2;
      font-weight: 600;
    }

    .trigger-value {
      font-weight: 800;
      font-size: 0.85rem;
      margin-left: 6px;
      color: #cdd6f4;
    }

    .trigger-desc {
      font-size: 0.75rem;
      color: #a6adc8;
      margin: 4px 0 0 0;
    }

    .action-plan {
      background: rgba(30,30,46,0.5);
      border: 1px solid #313244;
      border-left: 4px solid #89b4fa;
      padding: 16px;
      margin-bottom: 16px;
      border-radius: 4px 8px 8px 4px;
    }
    
    .action-plan.bullish { border-left-color: #a6e3a1; }
    .action-plan.bearish { border-left-color: #f38ba8; }

    .plan-header {
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 700;
      color: #9399b2;
      margin-bottom: 6px;
    }

    .plan-title {
      font-size: 1.1rem;
      font-weight: 800;
      color: #cdd6f4;
      margin-bottom: 8px;
    }
    
    .action-plan.bullish .plan-title { color: #a6e3a1; }
    .action-plan.bearish .plan-title { color: #f38ba8; }

    .plan-details {
      font-size: 0.85rem;
      color: #a6adc8;
      line-height: 1.5;
      margin: 0;
    }

    .psych-guard, .pyramid-plan, .scaling-plan {
      margin-top: 12px;
      padding: 10px;
      border-radius: 6px;
      font-size: 0.8rem;
      display: flex;
      align-items: flex-start;
      gap: 8px;
    }
    
    .psych-guard {
      background: rgba(243, 139, 168, 0.05); /* Red tint */
      border: 1px dashed rgba(243, 139, 168, 0.3);
      color: #f38ba8;
    }

    .pyramid-plan {
      background: rgba(166, 227, 161, 0.05); /* Green tint */
      border: 1px dashed rgba(166, 227, 161, 0.3);
      color: #a6e3a1;
    }

    .scaling-plan {
      background: rgba(203, 166, 247, 0.05); /* Purple tint */
      border: 1px dashed rgba(203, 166, 247, 0.3);
      color: #cba6f7;
    }
    
    .guard-text, .pyramid-text, .scaling-text {
      line-height: 1.4;
      color: #cdd6f4;
    }
    
    .guard-text strong {
      color: #f38ba8;
    }
    
    .pyramid-text strong {
      color: #a6e3a1;
    }

    .scaling-text strong {
      color: #cba6f7;
    }

    .reasons {
      padding: 16px;
      border-radius: 8px;
    }

    .highlight-reasons {
      background: rgba(137, 180, 250, 0.05);
      border: 1px dashed rgba(137, 180, 250, 0.3);
    }

    .reasons h4 {
      color: #cdd6f4;
      font-size: 0.9rem;
      margin: 0 0 8px 0;
    }

    .reasons ul {
      margin: 0;
      padding-left: 20px;
    }

    .reasons li {
      color: #a6adc8;
      font-size: 0.8rem;
      margin-bottom: 4px;
    }

    .tech-indicators-section {
      background: rgba(137, 180, 250, 0.05);
      border: 1px solid rgba(137, 180, 250, 0.1);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .tech-header {
      color: #89b4fa;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .tech-header::before {
      content: "🧠";
    }

    .tech-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      margin-bottom: 12px;
    }

    .tech-grid.pivot-matrix {
      grid-template-columns: repeat(3, 1fr);
      background: rgba(24, 24, 37, 0.5);
      border-radius: 8px;
      padding: 8px;
    }

    .tech-grid.fib-matrix {
      grid-template-columns: repeat(3, 1fr);
      background: rgba(24, 24, 37, 0.5);
      border-radius: 8px;
      padding: 8px;
    }

    .tech-item {
      display: flex;
      flex-direction: column;
    }

    .tech-label {
      font-size: 0.7rem;
      color: #9399b2;
    }

    .fib-header {
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid rgba(137, 180, 250, 0.2);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .fib-trend {
      font-size: 0.7rem;
      font-weight: 700;
    }
    
    .fib-trend.up { color: #a6e3a1; }
    .fib-trend.down { color: #f38ba8; }
    .fib-trend.flat { color: #9399b2; }

    .tech-value {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 0.85rem;
    }

    .tech-value.res { color: #f38ba8; }
    .tech-value.sup { color: #a6e3a1; }
    .tech-value.up { color: #a6e3a1; }
    .tech-value.down { color: #f38ba8; }
    .tech-value.ext { color: #cba6f7; }
    .tech-value.ret { color: #f9e2af; }
    .tech-value.swing { color: #89b4fa; }

    .breakout-badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 800;
      margin-bottom: 8px;
    }

    .breakout-badge.bullish {
      background: rgba(166, 227, 161, 0.2);
      color: #a6e3a1;
      border: 1px solid #a6e3a1;
    }

    .breakout-badge.bearish {
      background: rgba(243, 139, 168, 0.2);
      color: #f38ba8;
      border: 1px solid #f38ba8;
    }

    .tech-desc {
      font-size: 0.75rem;
      color: #a6adc8;
      border-top: 1px solid rgba(137, 180, 250, 0.1);
      padding-top: 8px;
    }

    .chart-action {
      margin-bottom: 20px;
    }

    .btn-chart {
      width: 100%;
      background: rgba(137, 180, 250, 0.1);
      border: 1px dashed rgba(137, 180, 250, 0.3);
      color: #89b4fa;
      padding: 10px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.2s;
    }

    .btn-chart:hover {
      background: rgba(137, 180, 250, 0.2);
    }

    .btn-chart.active {
      background: #89b4fa;
      color: #1e1e2e;
      border-style: solid;
    }

    .chart-wrapper {
      margin-bottom: 20px;
    }

    .chart-loading, .chart-error {
      height: 150px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #1e1e2e;
      border-radius: 8px;
      color: #9399b2;
      font-style: italic;
    }

    .news-section {
      background: rgba(69, 71, 90, 0.2);
      border-radius: 10px;
      padding: 12px;
      margin-bottom: 20px;
      border: 1px solid rgba(147, 153, 178, 0.1);
    }

    .news-header {
      font-size: 0.8rem;
      font-weight: 700;
      color: #fab387;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .news-header::before { content: "📰 "; }

    .news-sentiment-badge {
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .news-sentiment-badge.bullish { background: #a6e3a1; color: #1e1e2e; }
    .news-sentiment-badge.bearish { background: #f38ba8; color: #1e1e2e; }
    .news-sentiment-badge.neutral { background: #9399b2; color: #1e1e2e; }

    .news-summary {
      font-size: 0.75rem;
      color: #cdd6f4;
      margin-bottom: 12px;
    }

    .news-items {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .news-item-link {
      display: block;
      padding: 8px;
      background: rgba(49, 50, 68, 0.5);
      border-radius: 6px;
      transition: background 0.2s;
      cursor: pointer;
    }

    .news-item-link:hover {
      background: rgba(49, 50, 68, 0.8);
    }

    .news-item-title {
      font-size: 0.75rem;
      color: #89b4fa;
      display: block;
      margin-bottom: 4px;
      line-height: 1.4;
    }

    .news-item-meta {
      display: flex;
      justify-content: space-between;
      font-size: 0.65rem;
    }

    .news-source { color: #9399b2; }
    .news-sentiment.bullish { color: #a6e3a1; }
    .news-sentiment.bearish { color: #f38ba8; }
    .news-sentiment.neutral { color: #9399b2; }

    .news-modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(17, 17, 27, 0.8);
      backdrop-filter: blur(4px);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .news-modal-content {
      background: #1e1e2e;
      border: 1px solid #313244;
      border-radius: 12px;
      width: 100%;
      max-width: 1000px;
      height: 80vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
      overflow: hidden;
    }

    .news-modal-header {
      padding: 16px 24px;
      border-bottom: 1px solid #313244;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(30, 30, 46, 0.95);
    }

    .news-modal-header h3 {
      margin: 0;
      font-size: 1.1rem;
      color: #cdd6f4;
    }

    .close-btn {
      background: none;
      border: none;
      color: #a6adc8;
      font-size: 1.5rem;
      line-height: 1;
      cursor: pointer;
      transition: color 0.2s;
    }

    .close-btn:hover {
      color: #f38ba8;
    }

    .news-preview-card {
      max-width: 600px;
      height: auto;
      max-height: 80vh;
    }

    .news-preview-body {
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .news-preview-source {
      font-size: 0.8rem;
      color: #9399b2;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.5px;
    }

    .news-preview-title {
      font-size: 1.4rem;
      color: #cdd6f4;
      margin: 0;
      line-height: 1.4;
    }

    .news-preview-meta {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .news-preview-text {
      color: #a6adc8;
      font-size: 0.95rem;
      line-height: 1.5;
      padding: 16px;
      background: rgba(24, 24, 37, 0.5);
      border-radius: 8px;
      border: 1px dashed #313244;
      text-align: center;
      margin: 16px 0;
    }

    .btn-read-full {
      display: inline-block;
      width: 100%;
      text-align: center;
      padding: 12px 20px;
      background: #89b4fa;
      color: #1e1e2e;
      text-decoration: none;
      font-weight: 700;
      border-radius: 8px;
      transition: background 0.2s;
    }

    .btn-read-full:hover {
      background: #b4befe;
    }

    .pullback-warning-section {
      background: rgba(30, 30, 46, 0.6);
      border: 1px solid #313244;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
      transition: all 0.3s ease;
    }

    .pullback-warning-section.active-warning {
      border: 1px solid #fab387;
      background: rgba(250, 179, 135, 0.05);
      box-shadow: 0 0 15px rgba(250, 179, 135, 0.1);
    }

    .warning-header {
      color: #9399b2;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .active-warning .warning-header {
      color: #fab387;
    }

    .warning-score {
      margin-left: auto;
      font-size: 0.75rem;
      background: #313244;
      padding: 2px 8px;
      border-radius: 10px;
      color: #a6adc8;
    }

    .warning-score.risky {
      background: #fab387;
      color: #1e1e2e;
    }

    .warning-reasons {
      margin: 8px 0 0 0;
      padding-left: 18px;
      list-style-type: "•";
    }

    .warning-reasons li {
      color: #bac2de;
      font-size: 0.75rem;
      margin-bottom: 4px;
      padding-left: 6px;
    }

    .active-warning .warning-reasons li {
      color: #fab387;
    }
  `]
})
export class InstrumentCardComponent {
  @Input({ required: true }) analysis!: InstrumentAnalysis;
  @Output() refresh = new EventEmitter<string>();

  private marketAnalyzerService = inject(MarketAnalyzerService);

  showChart = false;
  chartData: ChartData[] = [];
  isLoadingChart = false;
  selectedNewsItem: NewsItem | null = null;

  openNewsModal(item: NewsItem) {
    this.selectedNewsItem = item;
  }

  closeNewsModal() {
    this.selectedNewsItem = null;
  }

  onRefresh() {
    this.refresh.emit(this.analysis.symbol);
  }

  getTimeAgo(timestamp: string): string {
    if (!timestamp) return 'Unknown';
    const updatedDate = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - updatedDate.getTime();

    // Convert to seconds
    const diffSecs = Math.floor(diffMs / 1000);

    if (diffSecs < 60) return `Just now`;
    if (diffSecs < 3600) {
      const mins = Math.floor(diffSecs / 60);
      return `${mins} min${mins !== 1 ? 's' : ''} ago`;
    }
    if (diffSecs < 86400) {
      const hours = Math.floor(diffSecs / 3600);
      return `${hours} hr${hours !== 1 ? 's' : ''} ago`;
    }
    const days = Math.floor(diffSecs / 86400);
    return `${days} day${days !== 1 ? 's' : ''} ago`;
  }

  toggleChart() {
    this.showChart = !this.showChart;
    if (this.showChart && this.chartData.length === 0) {
      this.isLoadingChart = true;
      this.marketAnalyzerService.getChartData(this.analysis.symbol).subscribe({
        next: (data) => {
          this.chartData = data;
          this.isLoadingChart = false;
        },
        error: (err) => {
          console.error('Error fetching chart data:', err);
          this.isLoadingChart = false;
        }
      });
    }
  }

  getCardClass(): string {
    return this.analysis.trade_signal.recommendation;
  }

  getSignalClass(): string {
    return this.analysis.trade_signal.recommendation;
  }

  getSignalIcon(): string {
    switch (this.analysis.trade_signal.recommendation) {
      case 'bullish': return '↑';
      case 'bearish': return '↓';
      default: return '→';
    }
  }

  getPriceChangeClass(): string {
    return this.analysis.daily_strength.price_change_percent >= 0 ? 'positive' : 'negative';
  }

  getScoreClass(): string {
    if (this.analysis.trade_signal.score > 20) return 'positive';
    if (this.analysis.trade_signal.score < -20) return 'negative';
    return 'neutral';
  }

  getAlphaClass(): string {
    if (!this.analysis.relative_strength) return '';
    const label = this.analysis.relative_strength.label.toLowerCase();
    if (label.includes('leader')) return 'leader';
    if (label.includes('laggard')) return 'laggard';
    return 'neutral';
  }

  get macroLabel(): string {
    return this.analysis.strategy_mode === 'long_term' ? 'Monthly' : 'Daily';
  }

  get pullbackLabel(): string {
    return this.analysis.strategy_mode === 'long_term' ? 'Weekly' : '4-Hour';
  }

  get executionLabel(): string {
    return this.analysis.strategy_mode === 'long_term' ? 'Daily' : '1-Hour';
  }

  getTrendClass(): string {
    return this.analysis.monthly_trend.direction;
  }

  getPullbackClass(): string {
    if (this.analysis.weekly_pullback.detected && this.analysis.weekly_pullback.near_support) {
      return 'bullish';
    }
    if (this.analysis.weekly_pullback.detected) {
      return 'neutral';
    }
    return 'neutral';
  }

  getStrengthClass(): string {
    return this.analysis.daily_strength.signal;
  }

  getPhaseClass(): string {
    return this.analysis.market_phase.phase;
  }

  getResistanceClass(): string {
    if (!this.analysis.technical_indicators) return '';
    return this.analysis.technical_indicators.least_resistance_line;
  }

  getBreakoutClass(): string {
    if (!this.analysis.technical_indicators) return '';
    const type = this.analysis.technical_indicators.trend_breakout;
    if (type.includes('bullish')) return 'bullish';
    if (type.includes('bearish')) return 'bearish';
    return '';
  }
}
