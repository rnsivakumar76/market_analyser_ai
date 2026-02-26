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
                <div class="trade-signal-mini">
                  <div class="signal-badge" [class]="getSignalClass()">
                    <span class="signal-icon">{{ getSignalIcon() }}</span>
                    <span class="signal-text">{{ analysis.trade_signal.recommendation.toUpperCase() }}</span>
                  </div>
                  <div class="score">
                    <span class="score-label">Conviction:</span>
                    <span class="score-value" [class]="getScoreClass()">{{ analysis.trade_signal.score }}</span>
                  </div>
                  @if (analysis.trade_signal.trade_worthy) {
                    <span class="trade-worthy">✓ Worthy</span>
                  }
                </div>
              </div>

              <!-- B. ACTION PLAN -->
              <div class="action-plan" [class]="getSignalClass()">
                <div class="plan-header">Strategic Action Plan</div>
                <div class="plan-title">{{ analysis.trade_signal.action_plan }}</div>

                @if (analysis.trade_signal.executive_summary) {
                  <div class="executive-summary-callout">
                    <span class="summary-icon">💡</span>
                    <p class="summary-text">{{ analysis.trade_signal.executive_summary }}</p>
                  </div>
                }

                <p class="plan-details">{{ analysis.trade_signal.action_plan_details }}</p>

                @if (analysis.trade_signal.psychological_guard) {
                  <div class="psych-guard">
                    <span class="guard-icon">🛡️</span>
                    <span class="guard-text"><strong>Psychological Rule:</strong> {{ analysis.trade_signal.psychological_guard }}</span>
                  </div>
                }
              </div>

              <!-- C. SIZING & RISK -->
              <div class="sizing-risk-row">
                @if (analysis.position_sizing) {
                  <div class="sizing-section">
                    <div class="sizing-header">Position Size</div>
                    <div class="sizing-grid">
                      <div class="sizing-item main">
                        <span class="sizing-label">Units</span>
                        <span class="sizing-value highlight">{{ analysis.position_sizing.suggested_units }}</span>
                      </div>
                      <div class="sizing-item">
                        <span class="sizing-label">Risk \${{ analysis.position_sizing.risk_amount }}</span>
                        <span class="sizing-value">{{ analysis.position_sizing.final_risk_percent }}%</span>
                      </div>
                    </div>
                  </div>
                }

                @if (analysis.volatility_risk) {
                  <div class="risk-section">
                    <div class="risk-header">Risk Management</div>
                    <div class="risk-grid">
                      <div class="risk-item">
                        <span class="risk-label">SL \${{ analysis.volatility_risk.stop_loss.toFixed(2) }}</span>
                        <span class="risk-value tp">TP \${{ analysis.volatility_risk.take_profit.toFixed(2) }}</span>
                      </div>
                      <div class="risk-item">
                        <span class="risk-label">R:R</span>
                        <span class="risk-value">{{ analysis.volatility_risk.risk_reward_ratio.toFixed(2) }}</span>
                      </div>
                    </div>
                  </div>
                }
              </div>

              <!-- D. MATRIX (The Facts) -->
              <div class="matrix-section">
                <div class="section-divider">Technical Matrix</div>
                <div class="indicators indicators-compact">
                  <div class="indicator-item">
                    <span class="ind-label">RSI</span>
                    <span class="ind-value">{{ analysis.daily_strength.rsi.toFixed(0) }}</span>
                  </div>
                  <div class="indicator-item">
                    <span class="ind-label">ADX</span>
                    <span class="ind-value" [class.strong]="analysis.daily_strength.adx > 25">{{ analysis.daily_strength.adx.toFixed(0) }}</span>
                  </div>
                  <div class="indicator-item">
                    <span class="ind-label">Vol</span>
                    <span class="ind-value">{{ analysis.daily_strength.volume_ratio.toFixed(1) }}x</span>
                  </div>
                </div>

                @if (analysis.technical_indicators) {
                  <div class="pivot-matrix-compact mt-12">
                    <div class="pivot-row">
                      <span class="p-label res">R3 \${{ analysis.technical_indicators.pivot_points.r3 }}</span>
                      <span class="p-label res">R2 \${{ analysis.technical_indicators.pivot_points.r2 }}</span>
                      <span class="p-label res">R1 \${{ analysis.technical_indicators.pivot_points.r1 }}</span>
                    </div>
                    <div class="pivot-row">
                      <span class="p-label sup">S3 \${{ analysis.technical_indicators.pivot_points.s3 }}</span>
                      <span class="p-label sup">S2 \${{ analysis.technical_indicators.pivot_points.s2 }}</span>
                      <span class="p-label sup">S1 \${{ analysis.technical_indicators.pivot_points.s1 }}</span>
                    </div>
                  </div>
                }
              </div>

              <!-- E. RESULTS (Backtest) -->
              <div class="results-section mt-16">
                <div class="section-divider">Backtest Probability</div>
                @if (analysis.backtest_results) {
                  <div class="backtest-summary">
                    <div class="b-stat">Win Rate: <span [class.good]="analysis.backtest_results.win_rate >= 50">{{ analysis.backtest_results.win_rate.toFixed(1) }}%</span></div>
                    <div class="b-stat">PF: {{ analysis.backtest_results.profit_factor }}</div>
                    <div class="b-stat">Trades: {{ analysis.backtest_results.total_trades }}</div>
                  </div>
                }
                
                @if (analysis.trade_signal.reasons.length > 0) {
                  <ul class="reasons-list">
                    @for (reason of analysis.trade_signal.reasons.slice(0, 3); track reason) {
                      <li>{{ reason }}</li>
                    }
                  </ul>
                }
              </div>
            </div>
          }

          @case ('insight') {
            <div class="tab-panel insight-tab">
              <!-- A. TREND INTELLIGENCE -->
              <app-multi-timeframe-overlay [analysis]="analysis"></app-multi-timeframe-overlay>

              <div class="trend-summary-compact mt-16">
                <div class="t-row">
                  <span class="t-label">Structure:</span>
                  <span class="t-value" [class]="getTrendClass()">{{ analysis.monthly_trend.direction.toUpperCase() }} ({{ analysis.market_phase.phase }})</span>
                </div>
                <p class="description t-desc">{{ analysis.monthly_trend.description }}</p>
              </div>

              <!-- B. FUNDAMENTALS & NEWS -->
              <div class="intelligence-section mt-16">
                <div class="section-divider">Intelligence & News</div>
                @if (analysis.fundamentals) {
                   <p class="description fund-desc-compact">
                    <strong>Economic Context:</strong> {{ analysis.fundamentals.description }}
                   </p>
                }

                @if (analysis.news_sentiment) {
                  <div class="news-list-compact mt-12">
                    @for (item of analysis.news_sentiment.news_items.slice(0, 3); track item.title) {
                      <div (click)="openNewsModal(item)" class="news-tiny-item">
                        <span class="n-title">{{ item.title }}</span>
                        <span class="n-sentiment" [class]="item.sentiment_label.toLowerCase()">{{ item.sentiment_label }}</span>
                      </div>
                    }
                  </div>
                }
              </div>

              <!-- C. INTERACTIVE CHART -->
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
    .card {
      background: #1e1e2e;
      border-radius: 12px;
      padding: 24px;
      border: 1px solid #313244;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }

    .card:hover {
      transform: translateY(-4px);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.4);
      border-color: #45475a;
    }

    .card.bullish { 
      border-left: 5px solid #a6e3a1; 
      background: linear-gradient(135deg, #1e1e2e 0%, #1e1e2e 80%, rgba(166, 227, 161, 0.05) 100%);
    }
    
    .card.bearish { 
      border-left: 5px solid #f38ba8; 
      background: linear-gradient(135deg, #1e1e2e 0%, #1e1e2e 80%, rgba(243, 139, 168, 0.05) 100%);
    }
    .card.neutral { border-left: 4px solid #f9e2af; }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
    }

    .symbol-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .symbol { font-size: 1.5rem; font-weight: 700; color: #cdd6f4; }
    
    .beta-status { font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; font-weight: 700; text-transform: uppercase; }
    .beta-status.good { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; border: 1px solid rgba(166, 227, 161, 0.2); }
    .beta-status.bad { background: rgba(243, 139, 168, 0.1); color: #f38ba8; border: 1px solid rgba(243, 139, 168, 0.2); }

    .alpha-status { font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; font-weight: 700; text-transform: uppercase; background: rgba(137, 180, 250, 0.1); color: #89b4fa; border: 1px solid rgba(137, 180, 250, 0.2); }
    .alpha-status.leader { background: rgba(249, 226, 175, 0.1); border-color: #f9e2af; color: #f9e2af; }
    .alpha-status.laggard { background: rgba(243, 139, 168, 0.1); border-color: #f38ba8; color: #f38ba8; }

    .name { font-size: 0.8rem; color: #6c7086; }
    .header-actions-right { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
    .price { font-size: 1.25rem; font-weight: 600; color: #cdd6f4; }
    .change { font-size: 0.9rem; font-weight: 600; }
    .change.positive { color: #a6e3a1; }
    .change.negative { color: #f38ba8; }

    .last-updated-row { display: flex; align-items: center; gap: 8px; }
    .last-updated-text { font-size: 0.7rem; color: #9399b2; font-style: italic; }
    .btn-refresh-local { background: rgba(137, 180, 250, 0.1); border: 1px solid rgba(137, 180, 250, 0.2); border-radius: 4px; padding: 4px 6px; cursor: pointer; color: #89b4fa; }

    .tabs-nav {
      display: flex;
      gap: 8px;
      margin-bottom: 20px;
      padding: 4px;
      background: rgba(24, 24, 37, 0.5);
      border-radius: 10px;
      border: 1px solid #313244;
    }

    .tab-btn {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 10px;
      border: none;
      background: transparent;
      color: #9399b2;
      font-weight: 700;
      font-size: 0.85rem;
      cursor: pointer;
      border-radius: 8px;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .tab-btn.active {
      background: #313244;
      color: #cdd6f4;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }

    .tab-icon { font-size: 1rem; }

    .section-divider {
      color: #6c7086;
      font-size: 0.7rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 24px 0 16px;
    }

    .section-divider::after {
      content: "";
      flex: 1;
      height: 1px;
      background: linear-gradient(90deg, #313244, transparent);
    }

    .trade-signal-mini { display: flex; align-items: center; gap: 16px; padding: 12px; background: rgba(24, 24, 37, 0.5); border-radius: 8px; }
    .signal-badge { display: flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; }
    .signal-badge.bullish { background: rgba(166, 227, 161, 0.2); color: #a6e3a1; }
    .signal-badge.bearish { background: rgba(243, 139, 168, 0.2); color: #f38ba8; }
    .signal-badge.neutral { background: rgba(249, 226, 175, 0.2); color: #f9e2af; }

    .score { display: flex; align-items: center; gap: 6px; }
    .score-label { color: #9399b2; font-size: 0.8rem; }
    .score-value { font-weight: 800; font-size: 1rem; }
    .score-value.positive { color: #a6e3a1; }
    .score-value.negative { color: #f38ba8; }

    .action-plan { background: rgba(30,30,46,0.5); border: 1px solid #313244; border-left: 4px solid #89b4fa; padding: 16px; margin: 20px 0; border-radius: 4px 8px 8px 4px; }
    .action-plan.bullish { border-left-color: #a6e3a1; }
    .action-plan.bearish { border-left-color: #f38ba8; }
    .plan-header { font-size: 0.75rem; text-transform: uppercase; color: #9399b2; margin-bottom: 6px; }
    .plan-title { font-size: 1.1rem; font-weight: 800; color: #cdd6f4; margin-bottom: 8px; }
    .plan-details { font-size: 0.85rem; color: #a6adc8; line-height: 1.5; }

    .executive-summary-callout { background: rgba(137, 180, 250, 0.1); border: 1px solid rgba(137, 180, 250, 0.2); border-radius: 8px; padding: 12px; margin-bottom: 12px; display: flex; gap: 10px; }
    .summary-text { font-size: 0.9rem; color: #cdd6f4; font-style: italic; margin: 0; }

    .sizing-risk-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }
    .sizing-section, .risk-section { background: rgba(24, 24, 37, 0.8); border: 1px solid #313244; border-radius: 8px; padding: 12px; }
    .sizing-header, .risk-header { font-size: 0.75rem; font-weight: 800; color: #9399b2; text-transform: uppercase; margin-bottom: 10px; }
    .sizing-grid, .risk-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .sizing-label, .risk-label { font-size: 0.65rem; color: #6c7086; }
    .sizing-value, .risk-value { font-weight: 700; font-size: 0.9rem; color: #cdd6f4; }
    .sizing-value.highlight { color: #fab387; font-size: 1rem; }
    .risk-value.tp { color: #a6e3a1; }

    .indicators-compact { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .indicator-item { background: #181825; padding: 8px; border-radius: 6px; text-align: center; border: 1px solid #313244; }
    .ind-label { font-size: 0.7rem; color: #6c7086; display: block; margin-bottom: 2px; }
    .ind-value { font-weight: 700; color: #cdd6f4; font-size: 0.9rem; }
    .ind-value.strong { color: #a6e3a1; }

    .pivot-matrix-compact { background: #181825; border-radius: 8px; padding: 10px; border: 1px solid #313244; }
    .pivot-row { display: flex; justify-content: space-between; gap: 4px; margin-bottom: 4px; }
    .p-label { font-size: 0.65rem; padding: 2px 4px; border-radius: 4px; flex: 1; text-align: center; font-weight: 700; }
    .p-label.res { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }
    .p-label.sup { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }

    .backtest-summary { display: flex; justify-content: space-between; padding: 12px; background: rgba(24, 24, 37, 0.5); border-radius: 8px; margin-bottom: 12px; }
    .b-stat { font-size: 0.8rem; font-weight: 700; color: #cdd6f4; }
    .b-stat span.good { color: #a6e3a1; }
    .reasons-list { list-style: none; padding: 0; margin: 0; }
    .reasons-list li { font-size: 0.8rem; color: #a6adc8; padding-left: 20px; position: relative; margin-bottom: 4px; }
    .reasons-list li::before { content: "✓"; position: absolute; left: 0; color: #a6e3a1; font-weight: 900; }

    .trend-summary-compact { padding: 12px; background: rgba(24, 24, 37, 0.5); border-radius: 8px; }
    .t-label { font-size: 0.8rem; color: #9399b2; margin-right: 8px; }
    .t-value { font-weight: 800; font-size: 0.85rem; color: #cba6f7; }
    .t-desc { font-size: 0.85rem; color: #a6adc8; line-height: 1.4; margin-top: 8px; }

    .news-tiny-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #181825; border-radius: 6px; margin-bottom: 8px; cursor: pointer; transition: background 0.2s; border: 1px solid #313244; }
    .news-tiny-item:hover { background: #313244; }
    .n-title { font-size: 0.8rem; color: #cdd6f4; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 75%; }
    .n-sentiment { font-size: 0.65rem; font-weight: 800; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
    .n-sentiment.positive { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }
    .n-sentiment.negative { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }

    .chart-container-embedded { border: 1px solid #313244; border-radius: 8px; overflow: hidden; background: #181825; }
    .btn-load-chart { width: 100%; padding: 30px; background: transparent; color: #89b4fa; font-weight: 800; cursor: pointer; border: none; }
    .chart-wrapper-embedded { min-height: 300px; padding: 10px; }

    .news-modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(17, 17, 27, 0.85); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 2000; }
    .news-modal-content { background: #1e1e2e; border: 1px solid #313244; border-radius: 12px; max-width: 600px; width: 90%; overflow: hidden; }
    .news-modal-header { padding: 16px; border-bottom: 1px solid #313244; display: flex; justify-content: space-between; align-items: center; }
    .news-preview-body { padding: 20px; }
    .btn-read-full { display: block; width: 100%; text-align: center; padding: 12px; background: #89b4fa; color: #1e1e2e; text-decoration: none; font-weight: 700; border-radius: 8px; margin-top: 16px; }

    @media (max-width: 600px) {
      .sizing-risk-row { grid-template-columns: 1fr; }
      .price { font-size: 1.1rem; }
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
