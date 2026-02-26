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

    .tabs-nav {
      display: flex;
      gap: 4px;
      margin-bottom: 20px;
      padding: 4px;
      background: rgba(24, 24, 37, 0.5);
      border-radius: 10px;
      overflow-x: auto;
      scrollbar-width: none;
    }

    .tabs-nav::-webkit-scrollbar { display: none; }

    .tab-btn {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      padding: 8px 12px;
      border: none;
      background: transparent;
      color: #9399b2;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      border-radius: 8px;
      transition: all 0.2s ease;
      min-width: 80px;
    }

    .tab-btn:hover {
      background: rgba(137, 180, 250, 0.1);
      color: #cdd6f4;
    }

    .tab-btn.active {
      background: #313244;
      color: #89b4fa;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
    }

    .tab-icon {
      font-size: 1.1rem;
    }

    .card-content-tabbed {
      min-height: 480px;
    }

    .tab-panel {
      animation: fadeIn 0.3s ease;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(5px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .signal-summary-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      background: rgba(49, 50, 68, 0.3);
      border-radius: 8px;
      border: 1px solid rgba(49, 50, 68, 0.5);
      margin-bottom: 4px;
    }

    .trade-signal-mini {
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }

    .sizing-risk-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    .chart-action-sticky {
      margin: 20px 0;
      padding-top: 16px;
      border-top: 1px solid #313244;
    }

    .mt-8 { margin-top: 8px; }
    .mt-12 { margin-top: 12px; }
    .mt-16 { margin-top: 16px; }
    .mb-16 { margin-bottom: 16px; }

    @media (max-width: 800px) {
      .sizing-risk-row {
        grid-template-columns: 1fr;
      }
      .tab-btn {
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
      letter-spacing: 0.5px;
    }

    .tab-btn.active {
      background: #313244;
      color: #cdd6f4;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }

    .tab-btn:hover:not(.active) {
      background: rgba(49, 50, 68, 0.5);
      color: #bac2de;
    }

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

    .analysis-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
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

    .indicators-compact {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }

    .pivot-matrix-compact {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 12px;
      background: #181825;
      border-radius: 8px;
      border: 1px solid #313244;
    }

    .pivot-row {
      display: flex;
      justify-content: space-between;
      gap: 8px;
    }

    .p-label {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      flex: 1;
      text-align: center;
    }

    .p-label.res { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }
    .p-label.sup { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }

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

    .executive-summary-callout {
      background: rgba(137, 180, 250, 0.1);
      border: 1px solid rgba(137, 180, 250, 0.2);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 12px;
      display: flex;
      align-items: flex-start;
      gap: 10px;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }

    .summary-icon {
      font-size: 1.2rem;
      flex-shrink: 0;
      margin-top: -2px;
    }

    .summary-text {
      font-size: 0.9rem;
      line-height: 1.5;
      color: #cdd6f4;
      font-weight: 500;
      margin: 0;
      font-style: italic;
    }

    .action-plan.bullish .executive-summary-callout {
      background: rgba(166, 227, 161, 0.08);
      border-color: rgba(166, 227, 161, 0.2);
    }
    
    .action-plan.bearish .executive-summary-callout {
      background: rgba(243, 139, 168, 0.08);
      border-color: rgba(243, 139, 168, 0.2);
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

    .backtest-summary {
      display: flex;
      justify-content: space-between;
      padding: 12px;
      background: #181825;
      border-radius: 8px;
      margin-bottom: 12px;
    }

    .b-stat {
      font-size: 0.8rem;
      font-weight: 700;
      color: #cdd6f4;
    }

    .b-stat span.good { color: #a6e3a1; }

    .reasons-list {
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .reasons-list li {
      font-size: 0.8rem;
      color: #9399b2;
      padding: 4px 0 4px 18px;
      position: relative;
    }

    .reasons-list li::before {
      content: "✓";
      position: absolute;
      left: 0;
      color: #a6e3a1;
      font-weight: 800;
    }

    .trend-summary-compact {
      padding: 12px;
      background: #181825;
      border-radius: 8px;
    }

    .t-row {
      display: flex;
      gap: 8px;
      margin-bottom: 4px;
    }

    .t-label { color: #6c7086; font-size: 0.8rem; font-weight: 700; }
    .t-value { font-weight: 800; font-size: 0.8rem; }
    .t-value.bullish { color: #a6e3a1; }
    .t-value.bearish { color: #f38ba8; }
    .t-desc { font-size: 0.8rem; line-height: 1.4; color: #a6adc8; }

    .news-tiny-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: #181825;
      border-radius: 6px;
      margin-bottom: 6px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .news-tiny-item:hover { background: #313244; }
    .n-title { font-size: 0.8rem; color: #cdd6f4; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70%; }
    .n-sentiment { font-size: 0.65rem; font-weight: 800; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
    .n-sentiment.positive { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }
    .n-sentiment.negative { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }

    .chart-container-embedded {
      background: #181825;
      border-radius: 8px;
      min-height: 100px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid #313244;
    }

    .btn-load-chart {
      width: 100%;
      padding: 20px;
      background: transparent;
      border: none;
      color: #89b4fa;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-load-chart:hover {
      background: rgba(137, 180, 250, 0.05);
      color: #b4befe;
    }

    .chart-wrapper-embedded {
      height: 300px;
      position: relative;
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
export class InstrumentCardComponent implements OnChanges {
  @Input({ required: true }) analysis!: InstrumentAnalysis;
  @Output() refresh = new EventEmitter<string>();

  private marketAnalyzerService = inject(MarketAnalyzerService);

  showChart = false;
  chartData: ChartData[] = [];
  isLoadingChart = false;
  selectedNewsItem: NewsItem | null = null;

  selectedTab: 'plan' | 'insight' = 'plan';

  setTab(tab: 'plan' | 'insight') {
    this.selectedTab = tab;
  }

  openNewsModal(item: NewsItem) {
    this.selectedNewsItem = item;
  }

  closeNewsModal() {
    this.selectedNewsItem = null;
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['analysis'] && !changes['analysis'].firstChange) {
      if (this.showChart) {
        this.refreshChart();
      }
    }
  }

  refreshChart() {
    this.isLoadingChart = true;
    this.marketAnalyzerService.getChartData(this.analysis.symbol).subscribe({
      next: (data) => {
        this.chartData = data;
        this.isLoadingChart = false;
      },
      error: (err) => {
        console.error('Error refreshing chart data:', err);
        this.isLoadingChart = false;
      }
    });
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
