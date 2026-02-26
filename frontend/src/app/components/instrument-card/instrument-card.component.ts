import { Component, Input, Output, EventEmitter, inject, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis, MarketAnalyzerService, ChartData, NewsItem } from '../../services/market-analyzer.service';
import { InstrumentChartComponent } from '../instrument-chart/instrument-chart.component';
import { MultiTimeframeOverlayComponent } from '../multi-timeframe-overlay/multi-timeframe-overlay.component';

@Component({
  selector: 'app-instrument-card',
  standalone: true,
  imports: [CommonModule, InstrumentChartComponent, MultiTimeframeOverlayComponent],
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

      <div class="tabs-nav">
        <button class="tab-btn" (click)="setTab('plan')" [class.active]="selectedTab === 'plan'">
          <span class="tab-icon">🎯</span> Tactical Plan
        </button>
        <button class="tab-btn" (click)="setTab('insight')" [class.active]="selectedTab === 'insight'">
          <span class="tab-icon">🧠</span> Insight & Data
        </button>
      </div>

      <!-- Main Content Area -->
      <div class="card-content-tabbed">
        @switch (selectedTab) {
          @case ('plan') {
            <div class="tab-panel action-tab">
              <!-- A. STRATEGIC SIGNAL -->
              <div class="signal-summary-row">
                <div class="trade-signal-mini" [class]="getSignalClass()">
                  <div class="signal-badge" [class]="getSignalClass()">
                    <span class="signal-icon">{{ getSignalIcon() }}</span>
                    <span class="signal-text">{{ analysis.trade_signal.recommendation.toUpperCase() }}</span>
                  </div>
                  <div class="score">
                    <span class="score-label">Score:</span>
                    <span class="score-value" [class]="getScoreClass()">{{ analysis.trade_signal.score }}</span>
                  </div>
                  @if (analysis.trade_signal.trade_worthy) {
                    <span class="trade-worthy-badge">✓ TRADABLE</span>
                  }
                </div>
              </div>

              <!-- B. ACTION PLAN -->
              <div class="action-plan-container" [class]="getSignalClass()">
                <div class="plan-card">
                  <div class="plan-header">Strategic Action Plan</div>
                  <div class="plan-title">{{ analysis.trade_signal.action_plan }}</div>

                  @if (analysis.trade_signal.executive_summary) {
                    <div class="summary-callout">
                      <span class="summary-icon">💡</span>
                      <p class="summary-text">{{ analysis.trade_signal.executive_summary }}</p>
                    </div>
                  }

                  <p class="plan-details">{{ analysis.trade_signal.action_plan_details }}</p>

                  <div class="rules-grid">
                    @if (analysis.trade_signal.psychological_guard) {
                      <div class="rule-item">
                        <span class="rule-icon">🛡️</span>
                        <div class="rule-content">
                          <strong>Psychological Rule:</strong>
                          <span>{{ analysis.trade_signal.psychological_guard }}</span>
                        </div>
                      </div>
                    }
                    @if (analysis.trade_signal.scaling_plan) {
                      <div class="rule-item">
                        <span class="rule-icon">⚖️</span>
                        <div class="rule-content">
                          <strong>Scaling Plan:</strong>
                          <span>{{ analysis.trade_signal.scaling_plan }}</span>
                        </div>
                      </div>
                    }
                  </div>
                </div>

                <!-- C. PULLBACK RISK -->
                @if (analysis.pullback_warning) {
                  <div class="pullback-risk-card" [class.warning]="analysis.pullback_warning.is_warning">
                    <div class="p-risk-header">
                      <span>⚠️ PULLBACK RISK ASSESSMENT</span>
                      <span class="p-risk-score">SCORE: {{ analysis.pullback_warning.warning_score }}/8</span>
                    </div>
                    <p class="p-risk-desc">{{ analysis.pullback_warning.description }}</p>
                  </div>
                }
              </div>

              <!-- D. SIZING & RISK -->
              <div class="data-grid-layout">
                @if (analysis.position_sizing) {
                  <div class="data-card sizing-card">
                    <div class="data-card-header">
                      <span class="icon">💰</span> RISK-ADJUSTED SIZING
                    </div>
                    <div class="data-grid">
                      <div class="data-item">
                        <span class="label">Suggested Units</span>
                        <span class="value highlight">{{ analysis.position_sizing.suggested_units }}</span>
                      </div>
                      <div class="data-item">
                        <span class="label">Risk Amount</span>
                        <span class="value">\${{ analysis.position_sizing.risk_amount }}</span>
                      </div>
                      <div class="data-item">
                        <span class="label">Risk %</span>
                        <span class="value">{{ analysis.position_sizing.final_risk_percent }}%</span>
                      </div>
                      <div class="data-item">
                        <span class="label">Corr. Penalty</span>
                        <span class="value" [class.negative]="analysis.position_sizing.correlation_penalty > 0">
                          -{{ (analysis.position_sizing.correlation_penalty * 100).toFixed(0) }}%
                        </span>
                      </div>
                    </div>
                  </div>
                }

                @if (analysis.volatility_risk) {
                  <div class="data-card risk-card">
                    <div class="data-card-header">
                      <span class="icon">🛡️</span> RISK & VOLATILITY
                    </div>
                    <div class="data-grid">
                      <div class="data-item">
                        <span class="label">ATR (14D)</span>
                        <span class="value">{{ analysis.volatility_risk.atr.toFixed(3) }}</span>
                      </div>
                      <div class="data-item">
                        <span class="label">Stop Loss</span>
                        <span class="value sl">\${{ analysis.volatility_risk.stop_loss.toFixed(2) }}</span>
                      </div>
                      <div class="data-item">
                        <span class="label">Take Profit</span>
                        <span class="value tp">\${{ analysis.volatility_risk.take_profit.toFixed(2) }}</span>
                      </div>
                      <div class="data-item">
                        <span class="label">RR Ratio</span>
                        <span class="value">{{ analysis.volatility_risk.risk_reward_ratio.toFixed(2) }}</span>
                      </div>
                    </div>
                  </div>
                }
              </div>

              <!-- E. TRUSTWORTHY SIGNALS -->
              <div class="trust-signals-section">
                <div class="section-divider">Trustworthy Signals</div>
                <div class="reasons-pill-container">
                  @for (reason of analysis.trade_signal.reasons; track reason) {
                    <div class="reason-pill">
                      <span class="pill-dot"></span>
                      {{ reason }}
                    </div>
                  }
                </div>
              </div>
            </div>

          }

          @case ('insight') {
            <div class="tab-panel insight-tab">
              <!-- A. TREND & ALIGNMENT -->
              <app-multi-timeframe-overlay [analysis]="analysis"></app-multi-timeframe-overlay>

              <!-- B. TECHNICAL MATRICES -->
              <div class="data-grid-layout mt-16">
                @if (analysis.technical_indicators) {
                  <div class="data-card pivot-card">
                    <div class="data-card-header">
                      <span class="icon">🎯</span> STRATEGIC PIVOT MATRIX
                    </div>
                    <div class="pivot-matrix-main">
                      <div class="pivot-row">
                        <div class="p-col"><span class="p-tag res">R3</span> \${{ analysis.technical_indicators.pivot_points.r3 }}</div>
                        <div class="p-col"><span class="p-tag res">R2</span> \${{ analysis.technical_indicators.pivot_points.r2 }}</div>
                        <div class="p-col"><span class="p-tag res">R1</span> \${{ analysis.technical_indicators.pivot_points.r1 }}</div>
                      </div>
                      <div class="pivot-row">
                        <div class="p-col"><span class="p-tag sup">S1</span> \${{ analysis.technical_indicators.pivot_points.s1 }}</div>
                        <div class="p-col"><span class="p-tag sup">S2</span> \${{ analysis.technical_indicators.pivot_points.s2 }}</div>
                        <div class="p-col"><span class="p-tag sup">S3</span> \${{ analysis.technical_indicators.pivot_points.s3 }}</div>
                      </div>
                      <div class="pivot-footer">
                        <span>Daily Pivot: <strong>\${{ analysis.technical_indicators.pivot_points.pivot }}</strong></span>
                        <span>Least Resistance: <strong [class]="analysis.technical_indicators.least_resistance_line">{{ analysis.technical_indicators.least_resistance_line.toUpperCase() }}</strong></span>
                      </div>
                    </div>
                  </div>

                  <div class="data-card fib-card">
                    <div class="data-card-header">
                      <span class="icon">📊</span> SWING FIBONACCI RANGES
                    </div>
                    @if (analysis.technical_indicators.fibonacci) {
                      <div class="fib-grid">
                        <div class="fib-item"><span class="label">Ext 1.618</span><span class="value">\${{ analysis.technical_indicators.fibonacci.ext_1618.toFixed(2) }}</span></div>
                        <div class="fib-item"><span class="label">Ext 1.272</span><span class="value">\${{ analysis.technical_indicators.fibonacci.ext_1272.toFixed(2) }}</span></div>
                        <div class="fib-item"><span class="label">Swing High</span><span class="value">\${{ analysis.technical_indicators.fibonacci.swing_high.toFixed(2) }}</span></div>
                        <div class="fib-item"><span class="label">Ret 38.2%</span><span class="value">\${{ analysis.technical_indicators.fibonacci.ret_382.toFixed(2) }}</span></div>
                        <div class="fib-item"><span class="label">Ret 61.8%</span><span class="value">\${{ analysis.technical_indicators.fibonacci.ret_618.toFixed(2) }}</span></div>
                        <div class="fib-item"><span class="label">Swing Low</span><span class="value">\${{ analysis.technical_indicators.fibonacci.swing_low.toFixed(2) }}</span></div>
                      </div>
                    }
                  </div>
                }
              </div>

              <!-- C. PROBABILITY & BACKTEST -->
              @if (analysis.backtest_results) {
                <div class="backtest-horizontal mt-16">
                  <div class="data-card-header">
                    <span class="icon">📈</span> STRATEGY PROBABILITY (1Y BACKTEST)
                  </div>
                  <div class="backtest-stats">
                    <div class="b-item">
                      <span class="label">Win Rate</span>
                      <span class="value" [class.good]="analysis.backtest_results.win_rate >= 50">{{ analysis.backtest_results.win_rate.toFixed(1) }}%</span>
                    </div>
                    <div class="b-item">
                      <span class="label">Total Trades</span>
                      <span class="value">{{ analysis.backtest_results.total_trades }}</span>
                    </div>
                    <div class="b-item">
                      <span class="label">Profit Factor</span>
                      <span class="value" [class.good]="analysis.backtest_results.profit_factor > 1.5">{{ analysis.backtest_results.profit_factor }}</span>
                    </div>
                  </div>
                  <p class="b-desc">{{ analysis.backtest_results.description }}</p>
                </div>
              }

              <!-- D. FUNDAMENTALS & NEWS -->
              <div class="intelligence-section mt-16">
                <div class="section-divider">Intelligence & Fundamentals</div>
                
                @if (analysis.fundamentals) {
                  <div class="fundamentals-context">
                    <div class="fund-header">
                      <span class="icon">🌍</span> FUNDAMENTAL CONTEXT
                      @if (analysis.fundamentals.has_high_impact_events) {
                        <span class="impact-badge high">HIGH IMPACT EVENTS</span>
                      }
                    </div>
                    <p class="fund-desc">{{ analysis.fundamentals.description }}</p>
                    @if (analysis.fundamentals.events.length > 0) {
                      <div class="event-list">
                        @for (event of analysis.fundamentals.events; track event) {
                          <div class="event-item">
                            <span class="event-dot"></span> {{ event }}
                          </div>
                        }
                      </div>
                    }
                  </div>
                }

                @if (analysis.news_sentiment) {
                  <div class="news-intelligence mt-16">
                    <div class="news-header-row">
                      <span class="news-title-text"><span class="icon">📰</span> News Intelligence</span>
                      <span class="sentiment-badge" [class]="analysis.news_sentiment.label.toLowerCase()">
                        {{ analysis.news_sentiment.label.toUpperCase() }}
                      </span>
                    </div>
                    <p class="sentiment-summary">{{ analysis.news_sentiment.sentiment_summary }}</p>
                    <div class="news-grid-compact">
                      @for (item of analysis.news_sentiment.news_items.slice(0, 3); track item.title) {
                        <div (click)="openNewsModal(item)" class="news-mini-card">
                          <span class="n-title">{{ item.title }}</span>
                          <span class="n-meta">{{ item.sentiment_label }} • {{ item.source }}</span>
                        </div>
                      }
                    </div>
                  </div>
                }
              </div>

              <!-- E. INTERACTIVE CHART -->
              <div class="embedded-chart-section mt-24">
                <div class="section-divider">Market Dynamics</div>
                <div class="chart-container-embedded">
                  <div class="chart-controls">
                    <button class="btn-load-chart" (click)="toggleChart()" *ngIf="!showChart">
                      🚀 Initialize {{ analysis.symbol }} Intelligence Chart
                    </button>
                  </div>
                  
                  @if (showChart) {
                    <div class="chart-wrapper-embedded">
                      @if (isLoadingChart) { <div class="chart-loading">Processing data...</div> }
                      @else if (chartData.length > 0) {
                        <app-instrument-chart [data]="chartData" [symbol]="analysis.symbol"></app-instrument-chart>
                      }
                      @else { <div class="chart-error">Unable to stream data.</div> }
                    </div>
                  }
                </div>
              </div>
            </div>

          }
        }
      </div>

      <!-- Footer for modal overlays -->
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
    .tab-panel { animation: fadeIn 0.3s ease-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

    /* Tactical Tab Styles */
    .signal-summary-row { margin-bottom: 20px; }
    .trade-signal-mini { 
      display: flex; align-items: center; justify-content: space-between; 
      padding: 16px; border-radius: 12px; border: 1px solid #313244;
      background: rgba(24, 24, 37, 0.6);
    }
    .trade-signal-mini.bullish { border-left: 4px solid #a6e3a1; }
    .trade-signal-mini.bearish { border-left: 4px solid #f38ba8; }
    .trade-signal-mini.neutral { border-left: 4px solid #f9e2af; }

    .signal-badge { display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 1.1rem; }
    .score-value { font-size: 1.4rem; font-weight: 900; }
    .trade-worthy-badge { 
      background: #fab387; color: #1e1e2e; padding: 4px 10px; 
      border-radius: 6px; font-weight: 900; font-size: 0.75rem; 
      box-shadow: 0 0 15px rgba(250, 179, 135, 0.3);
    }

    .action-plan-container { display: flex; flex-direction: column; gap: 16px; margin-bottom: 20px; }
    .plan-card { 
      background: rgba(30, 30, 46, 0.6); border: 1px solid #313244; 
      border-radius: 12px; padding: 20px;
    }
    .plan-header { font-size: 0.7rem; color: #9399b2; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; }
    .plan-title { font-size: 1.3rem; font-weight: 850; color: #cdd6f4; margin-bottom: 12px; }
    .summary-callout { 
      background: rgba(137, 180, 250, 0.1); border: 1px solid rgba(137, 180, 250, 0.2);
      border-radius: 8px; padding: 12px; margin-bottom: 16px; display: flex; gap: 12px;
    }
    .summary-text { font-size: 0.95rem; color: #cdd6f4; font-style: italic; margin: 0; line-height: 1.5; }
    .plan-details { font-size: 0.9rem; color: #a6adc8; line-height: 1.6; margin-bottom: 20px; }

    .rules-grid { display: grid; grid-template-columns: 1fr; gap: 12px; border-top: 1px solid #313244; pt: 16px; }
    .rule-item { display: flex; gap: 12px; align-items: flex-start; }
    .rule-icon { font-size: 1.2rem; }
    .rule-content { display: flex; flex-direction: column; gap: 2px; }
    .rule-content strong { font-size: 0.75rem; color: #89b4fa; text-transform: uppercase; }
    .rule-content span { font-size: 0.85rem; color: #cdd6f4; }

    .pullback-risk-card { 
      background: rgba(166, 227, 161, 0.05); border: 1px solid rgba(166, 227, 161, 0.15); 
      border-radius: 10px; padding: 16px;
    }
    .pullback-risk-card.warning { background: rgba(243, 139, 168, 0.05); border-color: rgba(243, 139, 168, 0.2); }
    .p-risk-header { display: flex; justify-content: space-between; font-weight: 800; font-size: 0.75rem; color: #9399b2; margin-bottom: 8px; }
    .p-risk-score { color: #fab387; }
    .p-risk-desc { font-size: 0.85rem; color: #a6adc8; margin: 0; }

    .data-grid-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .data-card { background: #181825; border: 1px solid #313244; border-radius: 12px; padding: 16px; }
    .data-card-header { font-size: 0.75rem; font-weight: 800; color: #9399b2; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
    .data-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .data-item { display: flex; flex-direction: column; gap: 4px; }
    .data-item .label { font-size: 0.65rem; color: #6c7086; text-transform: uppercase; }
    .data-item .value { font-size: 1rem; font-weight: 700; color: #cdd6f4; }
    .data-item .value.highlight { color: #fab387; font-size: 1.2rem; }
    .data-item .value.sl { color: #f38ba8; }
    .data-item .value.tp { color: #a6e3a1; }
    .data-item .value.negative { color: #f38ba8; }

    .trust-signals-section { margin-top: 24px; }
    .reasons-pill-container { display: flex; flex-wrap: wrap; gap: 8px; }
    .reason-pill { 
      background: rgba(49, 50, 68, 0.4); border: 1px solid #313244; 
      padding: 6px 12px; border-radius: 20px; font-size: 0.8rem; 
      color: #bac2de; display: flex; align-items: center; gap: 8px;
    }
    .pill-dot { width: 6px; height: 6px; border-radius: 50%; background: #a6e3a1; }

    /* Insight Tab Styles */
    .pivot-matrix-main { background: rgba(17, 17, 27, 0.4); border-radius: 8px; padding: 12px; }
    .pivot-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
    .p-col { font-size: 0.85rem; color: #cdd6f4; display: flex; items-center: center; gap: 8px; }
    .p-tag { font-size: 0.6rem; font-weight: 800; padding: 2px 4px; border-radius: 4px; width: 20px; text-align: center; }
    .p-tag.res { background: rgba(243, 139, 168, 0.15); color: #f38ba8; }
    .p-tag.sup { background: rgba(166, 227, 161, 0.15); color: #a6e3a1; }
    .pivot-footer { border-top: 1px solid #313244; padding-top: 8px; mt: 8px; display: flex; justify-content: space-between; font-size: 0.75rem; color: #9399b2; }
    .pivot-footer strong.up { color: #a6e3a1; }
    .pivot-footer strong.down { color: #f38ba8; }

    .fib-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .fib-item { display: flex; flex-direction: column; align-items: center; text-align: center; }
    .fib-item .label { font-size: 0.6rem; color: #6c7086; }
    .fib-item .value { font-size: 0.85rem; font-weight: 700; color: #cdd6f4; }

    .backtest-horizontal { background: #181825; border: 1px solid #313244; border-radius: 12px; padding: 16px; }
    .backtest-stats { display: flex; justify-content: space-between; margin-bottom: 12px; }
    .b-item { display: flex; flex-direction: column; gap: 4px; }
    .b-item .label { font-size: 0.7rem; color: #6c7086; }
    .b-item .value { font-size: 1.1rem; font-weight: 800; color: #cdd6f4; }
    .b-item .value.good { color: #a6e3a1; }
    .b-desc { font-size: 0.8rem; color: #9399b2; font-style: italic; margin: 0; }

    .fundamentals-context { background: rgba(30, 30, 46, 0.4); border: 1px solid #313244; border-radius: 12px; padding: 16px; }
    .fund-header { font-size: 0.8rem; font-weight: 800; color: #cdd6f4; margin-bottom: 12px; display: flex; align-items: center; gap: 10px; }
    .impact-badge { font-size: 0.6rem; padding: 2px 6px; border-radius: 4px; }
    .impact-badge.high { background: #f38ba8; color: #11111b; }
    .fund-desc { font-size: 0.85rem; color: #a6adc8; line-height: 1.5; margin-bottom: 12px; }
    .event-list { display: flex; flex-direction: column; gap: 6px; border-top: 1px solid #313244; padding-top: 12px; }
    .event-item { font-size: 0.8rem; color: #bac2de; display: flex; align-items: center; gap: 8px; }
    .event-dot { width: 4px; height: 4px; border-radius: 50%; background: #fab387; }

    .news-intelligence { background: rgba(17, 17, 27, 0.4); border-radius: 12px; border: 1px solid #313244; padding: 16px; }
    .news-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .news-title-text { font-size: 0.85rem; font-weight: 800; color: #cdd6f4; }
    .sentiment-badge { font-size: 0.65rem; font-weight: 800; padding: 2px 8px; border-radius: 4px; }
    .sentiment-badge.bullish { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }
    .sentiment-badge.bearish { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }
    .sentiment-summary { font-size: 0.8rem; color: #9399b2; font-style: italic; margin-bottom: 16px; line-height: 1.4; }
    .news-grid-compact { display: flex; flex-direction: column; gap: 8px; }
    .news-mini-card { background: #1e1e2e; border: 1px solid #313244; padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
    .news-mini-card:hover { border-color: #89b4fa; transform: translateX(4px); }
    .news-mini-card .n-title { font-size: 0.8rem; color: #cdd6f4; display: block; margin-bottom: 4px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; }
    .news-mini-card .n-meta { font-size: 0.65rem; color: #6c7086; }

    @media (max-width: 600px) {
      .data-grid-layout { grid-template-columns: 1fr; }
      .fib-grid { grid-template-columns: 1fr 1fr; }
      .backtest-stats { flex-direction: column; gap: 12px; }
    }
  `]
})
export class InstrumentCardComponent implements OnChanges {
  @Input() analysis!: InstrumentAnalysis;
  @Output() refresh = new EventEmitter<string>();

  private marketAnalyzerService = inject(MarketAnalyzerService);

  selectedTab: 'plan' | 'insight' = 'plan';
  showChart = false;
  isLoadingChart = false;
  chartData: ChartData[] = [];
  selectedNewsItem: NewsItem | null = null;

  ngOnChanges(changes: SimpleChanges) {
    if (changes['analysis'] && !changes['analysis'].firstChange) {
      if (this.showChart && this.chartData.length === 0) {
        this.fetchChartData();
      }
    }
  }

  setTab(tab: 'plan' | 'insight') {
    this.selectedTab = tab;
  }

  toggleChart() {
    this.showChart = !this.showChart;
    if (this.showChart && this.chartData.length === 0) {
      this.fetchChartData();
    }
  }

  private fetchChartData() {
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

  openNewsModal(item: NewsItem) {
    this.selectedNewsItem = item;
  }

  closeNewsModal() {
    this.selectedNewsItem = null;
  }

  onRefresh() {
    this.refresh.emit(this.analysis.symbol);
  }

  // CSS Class Helpers
  getCardClass(): string {
    return this.analysis.trade_signal.recommendation.toLowerCase();
  }

  getTrendClass(): string {
    return this.analysis.monthly_trend.direction.toLowerCase();
  }

  getPhaseClass(): string {
    return this.analysis.market_phase.phase.toLowerCase().replace(' ', '-');
  }

  getStrengthClass(): string {
    return this.analysis.daily_strength.signal.toLowerCase();
  }

  getSignalClass(): string {
    return this.analysis.trade_signal.recommendation.toLowerCase();
  }

  getSignalIcon(): string {
    const rec = this.analysis.trade_signal.recommendation.toLowerCase();
    if (rec.includes('buy') || rec.includes('long')) return '🚀';
    if (rec.includes('sell') || rec.includes('short')) return '⚠️';
    return '⚖️';
  }

  getScoreClass(): string {
    const score = this.analysis.trade_signal.score;
    if (score >= 7) return 'positive';
    if (score <= 4) return 'negative';
    return 'neutral';
  }

  getPriceChangeClass(): string {
    return this.analysis.daily_strength.price_change_percent > 0 ? 'positive' : 'negative';
  }

  getAlphaClass(): string {
    if (!this.analysis.relative_strength) return '';
    return this.analysis.relative_strength.alpha > 0 ? 'leader' : 'laggard';
  }

  get pullbackLabel(): string {
    if (this.analysis.weekly_pullback.detected) return 'Range Entry Area';
    return 'Extended from Support';
  }

  get macroLabel(): string {
    return this.analysis.monthly_trend.direction.toLowerCase() === 'bullish' ? 'Stable Accumulation' : 'Risk Warning';
  }

  get executionLabel(): string {
    return this.analysis.daily_strength.signal.toLowerCase() === 'bullish' ? 'Execution Ready' : 'Wait for Setup';
  }

  getTimeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return date.toLocaleDateString();
  }
}
