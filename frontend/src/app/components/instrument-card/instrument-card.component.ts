import { Component, Input, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis, MarketAnalyzerService, ChartData } from '../../services/market-analyzer.service';
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
          </div>
          <span class="name">{{ analysis.name }}</span>
        </div>
        <div class="price-info">
          <span class="price">\${{ analysis.current_price.toFixed(2) }}</span>
          <span class="change" [class]="getPriceChangeClass()">
            {{ analysis.daily_strength.price_change_percent > 0 ? '+' : '' }}{{ analysis.daily_strength.price_change_percent.toFixed(2) }}%
          </span>
        </div>
      </div>

      <div class="card-content">
        <!-- Main Column (Left) -->
        <div class="main-column">
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

          <div class="analysis-grid">
            <div class="analysis-item">
              <div class="analysis-header">
                <span class="indicator" [class]="getTrendClass()">●</span>
                <span class="label">Monthly Trend</span>
              </div>
              <p class="description">{{ analysis.monthly_trend.description }}</p>
            </div>

            <div class="analysis-item phase-item">
              <div class="analysis-header">
                <span class="phase-badge" [class]="getPhaseClass()">
                  {{ analysis.market_phase.phase.toUpperCase() }}
                </span>
                <span class="label">Market Structure Phase</span>
              </div>
              <p class="description">{{ analysis.market_phase.description }}</p>
            </div>

            <div class="analysis-item">
              <div class="analysis-header">
                <span class="indicator" [class]="getPullbackClass()">●</span>
                <span class="label">Weekly Pullback</span>
              </div>
              <p class="description">{{ analysis.weekly_pullback.description }}</p>
            </div>

            <div class="analysis-item">
              <div class="analysis-header">
                <span class="indicator" [class]="getStrengthClass()">●</span>
                <span class="label">Daily Strength</span>
              </div>
              <p class="description">{{ analysis.daily_strength.description }}</p>
            </div>
          </div>

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
                  <div (click)="openNewsModal(item.url)" class="news-item-link">
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

        <!-- Side Column (Right) -->
        <div class="side-column">
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

          @if (analysis.trade_signal.reasons.length > 0) {
            <div class="reasons highlight-reasons">
              <h4>Trustworthy Indicators</h4>
              <ul>
                @for (reason of analysis.trade_signal.reasons; track reason) {
                  <li>{{ reason }}</li>
                }
              </ul>
            </div>
          }

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

          @if (analysis.technical_indicators) {
            <div class="tech-indicators-section">
              <div class="tech-header">Strategic Pivot & Breakout</div>
              <div class="tech-grid">
                <div class="tech-item pivot-main">
                  <span class="tech-label">Pivot Point</span>
                  <span class="tech-value">\${{ analysis.technical_indicators.pivot_points.pivot }}</span>
                </div>
                <div class="tech-item">
                  <span class="tech-label">Resistance 1</span>
                  <span class="tech-value res">\${{ analysis.technical_indicators.pivot_points.r1 }}</span>
                </div>
                <div class="tech-item">
                  <span class="tech-label">Support 1</span>
                  <span class="tech-value sup">\${{ analysis.technical_indicators.pivot_points.s1 }}</span>
                </div>
                <div class="tech-item">
                  <span class="tech-label">LLR</span>
                  <span class="tech-value" [class]="getResistanceClass()">
                    {{ analysis.technical_indicators.least_resistance_line.toUpperCase() }}
                  </span>
                </div>
              </div>
              
              @if (analysis.technical_indicators.trend_breakout !== 'none') {
                <div class="breakout-badge" [class]="getBreakoutClass()">
                  🎯 {{ analysis.technical_indicators.trend_breakout.replace('_', ' ').toUpperCase() }} 
                  ({{ (analysis.technical_indicators.breakout_confidence * 100).toFixed(0) }}%)
                </div>
              }
              <p class="description tech-desc">{{ analysis.technical_indicators.description }}</p>
            </div>
          }

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

          @if (analysis.candle_patterns && analysis.candle_patterns.pattern !== 'none') {
            <div class="candle-trigger" [class.bullish]="analysis.candle_patterns.is_bullish === true" [class.bearish]="analysis.candle_patterns.is_bullish === false">
              <span class="trigger-label">Trigger Candle:</span>
              <span class="trigger-value">{{ analysis.candle_patterns.pattern.replace('_', ' ').toUpperCase() }}</span>
              <p class="trigger-desc">{{ analysis.candle_patterns.description }}</p>
            </div>
          }
        </div>
      </div>
      
      @if (selectedNewsUrl) {
        <div class="news-modal-overlay" (click)="closeNewsModal()">
          <div class="news-modal-content" (click)="$event.stopPropagation()">
            <div class="news-modal-header">
              <h3>Intelligence Viewer</h3>
              <button class="close-btn" (click)="closeNewsModal()">×</button>
            </div>
            <iframe [src]="selectedNewsUrl" class="news-iframe"></iframe>
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

    .main-column {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .side-column {
      display: flex;
      flex-direction: column;
      gap: 16px;
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
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 12px;
    }

    .tech-item {
      display: flex;
      flex-direction: column;
    }

    .tech-label {
      font-size: 0.7rem;
      color: #9399b2;
    }

    .tech-value {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 0.85rem;
    }

    .tech-value.res { color: #f38ba8; }
    .tech-value.sup { color: #a6e3a1; }
    .tech-value.up { color: #a6e3a1; }
    .tech-value.down { color: #f38ba8; }

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

    .news-iframe {
      flex: 1;
      width: 100%;
      border: none;
      background: #ffffff; /* News sites expect white bg */
    }
  `]
})
export class InstrumentCardComponent {
  @Input({ required: true }) analysis!: InstrumentAnalysis;

  private marketAnalyzerService = inject(MarketAnalyzerService);
  private sanitizer = inject(DomSanitizer);

  showChart = false;
  chartData: ChartData[] = [];
  isLoadingChart = false;
  selectedNewsUrl: SafeResourceUrl | null = null;

  openNewsModal(url: string) {
    this.selectedNewsUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

  closeNewsModal() {
    this.selectedNewsUrl = null;
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
