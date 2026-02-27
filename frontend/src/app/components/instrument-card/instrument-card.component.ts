import { Component, Input, Output, EventEmitter, inject, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis, MarketAnalyzerService, ChartData, NewsItem } from '../../services/market-analyzer.service';
import { InstrumentChartComponent, ChartOverlayLevel } from '../instrument-chart/instrument-chart.component';
import { MultiTimeframeOverlayComponent } from '../multi-timeframe-overlay/multi-timeframe-overlay.component';
import { TradeJournalComponent } from '../trade-journal/trade-journal.component';

@Component({
  selector: 'app-instrument-card',
  standalone: true,
  imports: [CommonModule, InstrumentChartComponent, MultiTimeframeOverlayComponent, TradeJournalComponent],
  template: `
    <div class="instrument-view-container">
      <!-- Top Multi-Timeframe Area (from Image 1 & 2 layout) -->
      <div class="mtf-top-card">
        <app-multi-timeframe-overlay [analysis]="analysis"></app-multi-timeframe-overlay>
      </div>

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
            <!-- Candle Pattern Badge -->
            @if (analysis.candle_patterns?.pattern && analysis.candle_patterns.pattern !== 'None') {
              <span class="candle-badge" [class]="analysis.candle_patterns.is_bullish === true ? 'bull' : analysis.candle_patterns.is_bullish === false ? 'bear' : 'neutral'"
                    [title]="analysis.candle_patterns.description">
                {{ analysis.candle_patterns.is_bullish === true ? '🕯️📈' : analysis.candle_patterns.is_bullish === false ? '🕯️📉' : '🕯️' }}
                {{ analysis.candle_patterns.pattern }}
              </span>
            }
          </div>
          <span class="name">{{ analysis.name }}</span>
        </div>
        <div class="header-actions-right">
          <!-- Move Signal Score Badge to Header -->
          <div class="signal-score-badge header-badge" [class]="getSignalClass()">
            <span class="s-label">{{ analysis.trade_signal.recommendation.toUpperCase() }}</span>
            <span class="s-score">Score: <strong>{{ analysis.trade_signal.score }}</strong></span>
          </div>

          <div class="price-info-block">
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
      </div>

      <div class="tabs-nav">
        <button class="tab-btn" (click)="setTab('plan')" [class.active]="selectedTab === 'plan'">
          <span class="tab-icon">🎯</span> Tactical Plan
        </button>
        <button class="tab-btn" (click)="setTab('insight')" [class.active]="selectedTab === 'insight'">
          <span class="tab-icon">🧠</span> Insight & Data
        </button>
        <div class="strategy-mode-toggle">
          <button class="sm-btn" [class.active]="analysis.strategy_mode === 'short_term'"
            title="Short-Term (Daily/4H/1H)" (click)="switchMode('short_term')">⚡ Short</button>
          <button class="sm-btn" [class.active]="analysis.strategy_mode === 'long_term'"
            title="Long-Term (Monthly/Weekly/Daily)" (click)="switchMode('long_term')">📈 Long</button>
        </div>
      </div>

      <!-- Main Content Area -->
      <div class="card-content-tabbed">
        @switch (selectedTab) {
          @case ('plan') {
            <div class="tab-panel action-tab">
              <div class="tactical-grid">
                <!-- LEFT COLUMN: STRATEGY & NARRATIVE -->
                <div class="tactical-left">
                  <!-- 1. ACTION PLAN -->
                  <div class="section-card strategy-plan-card" [class]="getSignalClass()">
                    <div class="card-header-mini">STRATEGIC ACTION PLAN</div>
                    <div class="plan-hero-text">{{ analysis.trade_signal.action_plan }}</div>
                    <p class="plan-sub-text">{{ analysis.trade_signal.action_plan_details }}</p>

                    <div class="rule-box" *ngIf="analysis.trade_signal.psychological_guard">
                       <span class="icon">💡</span>
                       <div class="rule-text">
                         <strong>Psychological Rule:</strong> {{ analysis.trade_signal.psychological_guard }}
                       </div>
                    </div>

                    <div class="rule-box scaling" *ngIf="analysis.trade_signal.scaling_plan">
                       <span class="icon">⚖️</span>
                       <div class="rule-text">
                         <strong>Scaling Plan:</strong> {{ analysis.trade_signal.scaling_plan }}
                       </div>
                    </div>
                  </div>

                  <!-- 2. PULLBACK RISK -->
                  <div class="section-card pullback-assessment-card" [class.warning]="analysis.pullback_warning?.is_warning">
                    <div class="p-header">
                      <span class="p-title">⚠️ PULLBACK RISK ASSESSMENT</span>
                      <span class="p-score">SCORE: {{ analysis.pullback_warning?.warning_score || 0 }}/8</span>
                    </div>
                    <p class="p-desc">
                      {{ analysis.pullback_warning?.description || 'Momentum is healthy. No immediate pullback signals detected.' }}
                    </p>
                  </div>

                  <!-- 3. CHART LINK + LOG TO JOURNAL -->
                  <div class="action-btn-row">
                    <button class="btn-chart-link" (click)="setTab('insight')">
                      📊 View Chart
                    </button>
                    <button class="btn-journal" (click)="openJournalModal()">
                      📒 Log to Journal
                    </button>
                  </div>

                  <!-- 4. NEWS INTELLIGENCE -->
                  <div class="section-card news-intel-card">
                    <div class="news-header">
                      <span class="news-title"><span class="icon">📰</span> News Intelligence</span>
                      <span class="sentiment-tag" [class]="analysis.news_sentiment?.label?.toLowerCase() || 'neutral'">
                        {{ analysis.news_sentiment?.label || 'NEUTRAL' }}
                      </span>
                    </div>
                    <p class="sentiment-brief">{{ analysis.news_sentiment?.sentiment_summary }}</p>
                    <div class="news-mini-list">
                      @for (item of analysis.news_sentiment?.news_items?.slice(0, 3); track item.title) {
                        <div class="news-item-row" (click)="openNewsModal(item)">
                          <div class="n-info">
                            <span class="n-title">{{ item.title }}</span>
                            <span class="n-source">{{ item.source }} • 4 hours ago</span>
                          </div>
                          <span class="n-status" [class]="item.sentiment_label.toLowerCase()">{{ item.sentiment_label }}</span>
                        </div>
                      }
                    </div>
                  </div>
                </div>

                <!-- RIGHT COLUMN: DATA & RISK -->
                <div class="tactical-right">
                  <!-- 1. RISK-ADJUSTED SIZING -->
                  <div class="section-card data-card sizing-card">
                    <div class="data-header"><span class="icon">⚖️</span> RISK-ADJUSTED SIZING</div>
                    <div class="data-row-grid">
                      <div class="data-col"><span class="label">Suggested Units</span><span class="value accent">{{ analysis.position_sizing?.suggested_units }}</span></div>
                      <div class="data-col"><span class="label">Risk Amount</span><span class="value">\${{ analysis.position_sizing?.risk_amount }}</span></div>
                      <div class="data-col"><span class="label">Risk %</span><span class="value">{{ analysis.position_sizing?.final_risk_percent }}%</span></div>
                      <div class="data-col"><span class="label">Corr. Penalty</span><span class="value">-{{ (analysis.position_sizing?.correlation_penalty || 0) * 100 }}%</span></div>
                    </div>
                    <div class="sizing-footer">Risk {{ analysis.position_sizing?.final_risk_percent }}% of portfolio. Full size allocated — independent signal.</div>
                  </div>

                  <!-- 2. RISK & VOLATILITY MANAGEMENT -->
                  <div class="section-card data-card volatility-card">
                    <div class="data-header"><span class="icon">🛡️</span> RISK & VOLATILITY MANAGEMENT</div>
                    <div class="data-row-grid">
                      <div class="data-col"><span class="label">ATR (14D)</span><span class="value">{{ analysis.volatility_risk.atr.toFixed(3) }}</span></div>
                      <div class="data-col"><span class="label">Stop Loss</span><span class="value bearish">\${{ analysis.volatility_risk.stop_loss.toFixed(2) }}</span></div>
                      <div class="data-col"><span class="label">Take Profit</span><span class="value bullish">\${{ analysis.volatility_risk.take_profit.toFixed(2) }}</span></div>
                      <div class="data-col"><span class="label">RR Ratio</span><span class="value">{{ analysis.volatility_risk.risk_reward_ratio.toFixed(2) }}</span></div>
                    </div>
                    <div class="sizing-footer">Neutral market. ATR is {{ analysis.volatility_risk.atr.toFixed(2) }}. Expect daily swings.</div>
                  </div>

                  <!-- 3. FUNDAMENTAL CONTEXT (ECONOMIC DATA) -->
                  <div class="section-card data-card fundamentals-card">
                    <div class="data-header"><span class="icon">🌍</span> FUNDAMENTAL CONTEXT</div>
                    @if (analysis.fundamentals?.has_high_impact_events) {
                      <div class="impact-warning">WARNING! High volatility expected: Economic events today.</div>
                    }
                    <div class="event-stack">
                      @for (event of analysis.fundamentals?.events; track event) {
                        <div class="event-line">
                          <span class="icon">🔔</span> {{ event }}
                        </div>
                      }
                    </div>
                    <p class="fund-summary">{{ analysis.fundamentals?.description }}</p>
                  </div>

                  <!-- 4. TRUSTWORTHY SIGNALS -->
                  <div class="section-card data-card trust-signals-card">
                    <div class="data-header">Trustworthy Signals</div>
                    <ul class="trust-list">
                      @for (reason of analysis.trade_signal.reasons; track reason) {
                        <li>{{ reason }}</li>
                      }
                    </ul>
                  </div>

                  <!-- 5. INLINE METRICS -->
                  <div class="inline-metrics-row">
                    <div class="m-item"><span class="l">RSI</span><span class="v">{{ analysis.daily_strength.rsi.toFixed(1) }}</span></div>
                    <div class="m-item"><span class="l">ADX</span><span class="v">{{ analysis.daily_strength.adx.toFixed(1) }}</span></div>
                    <div class="m-item"><span class="l">Volume</span><span class="v">{{ analysis.daily_strength.volume_ratio.toFixed(2) }}x</span></div>
                    <div class="m-item"><span class="l">20 MA</span><span class="v">\${{ analysis.current_price.toFixed(2) }}</span></div>
                  </div>
                </div>
              </div>
            </div>


          }

          @case ('insight') {
            <div class="tab-panel insight-tab">
              <div class="insight-layout">
                <div class="insight-top-grid">
                   @if (analysis.technical_indicators) {
                    <div class="section-card data-card pivot-card">
                      <div class="data-header"><span class="icon">🎯</span> STRATEGIC PIVOT MATRIX</div>
                      <div class="pivot-grid-main">
                        <div class="pivot-column">
                          <div class="p-item"><span class="t res">R3</span> <span class="v">\${{ analysis.technical_indicators.pivot_points.r3 }}</span><button class="bell-btn" (click)="addLevelAlert('pivot_r3', analysis.technical_indicators!.pivot_points.r3)" title="Alert at R3">🔔</button></div>
                          <div class="p-item"><span class="t res">R2</span> <span class="v">\${{ analysis.technical_indicators.pivot_points.r2 }}</span><button class="bell-btn" (click)="addLevelAlert('pivot_r2', analysis.technical_indicators!.pivot_points.r2)" title="Alert at R2">🔔</button></div>
                          <div class="p-item"><span class="t res">R1</span> <span class="v">\${{ analysis.technical_indicators.pivot_points.r1 }}</span><button class="bell-btn" (click)="addLevelAlert('pivot_r1', analysis.technical_indicators!.pivot_points.r1)" title="Alert at R1">🔔</button></div>
                        </div>
                        <div class="pivot-column">
                          <div class="p-item"><span class="t sup">S1</span> <span class="v">\${{ analysis.technical_indicators.pivot_points.s1 }}</span><button class="bell-btn" (click)="addLevelAlert('pivot_s1', analysis.technical_indicators!.pivot_points.s1)" title="Alert at S1">🔔</button></div>
                          <div class="p-item"><span class="t sup">S2</span> <span class="v">\${{ analysis.technical_indicators.pivot_points.s2 }}</span><button class="bell-btn" (click)="addLevelAlert('pivot_s2', analysis.technical_indicators!.pivot_points.s2)" title="Alert at S2">🔔</button></div>
                          <div class="p-item"><span class="t sup">S3</span> <span class="v">\${{ analysis.technical_indicators.pivot_points.s3 }}</span><button class="bell-btn" (click)="addLevelAlert('pivot_s3', analysis.technical_indicators!.pivot_points.s3)" title="Alert at S3">🔔</button></div>
                        </div>
                      </div>
                      <div class="pivot-footer">
                        <span>Daily Pivot: \${{ analysis.technical_indicators.pivot_points.pivot }}</span>
                        <span>Resistance Line: <strong [class]="analysis.technical_indicators.least_resistance_line">{{ analysis.technical_indicators.least_resistance_line.toUpperCase() }}</strong></span>
                      </div>
                    </div>

                    <div class="section-card data-card fib-card">
                      <div class="data-header"><span class="icon">📊</span> SWING FIBONACCI RANGES</div>
                      <div class="fib-grid-main">
                        <div class="f-box ext"><span class="l">Ext 1.618</span><span class="v">\${{ analysis.technical_indicators.fibonacci?.ext_1618?.toFixed(2) }}</span></div>
                        <div class="f-box ext"><span class="l">Ext 1.272</span><span class="v">\${{ analysis.technical_indicators.fibonacci?.ext_1272?.toFixed(2) }}</span></div>
                        <div class="f-box high"><span class="l">Swing High</span><span class="v">\${{ analysis.technical_indicators.fibonacci?.swing_high?.toFixed(2) }}</span></div>
                        <div class="f-box ret"><span class="l">Ret 38.2%</span><span class="v">\${{ analysis.technical_indicators.fibonacci?.ret_382?.toFixed(2) }}</span></div>
                        <div class="f-box ret"><span class="l">Ret 61.8%</span><span class="v">\${{ analysis.technical_indicators.fibonacci?.ret_618?.toFixed(2) }}</span></div>
                        <div class="f-box low"><span class="l">Swing Low</span><span class="v">\${{ analysis.technical_indicators.fibonacci?.swing_low?.toFixed(2) }}</span></div>
                      </div>
                    </div>
                  }
                </div>

                <div class="section-card backtest-card mt-16">
                  <div class="data-header"><span class="icon">📈</span> STRATEGY PROBABILITY (1Y BACKTEST)</div>
                  <div class="backtest-layout">
                    <div class="backtest-stats-row">
                      <div class="b-stat"><span class="tl">Win Rate</span><span class="tv highlight">{{ analysis.backtest_results?.win_rate?.toFixed(1) }}%</span></div>
                      <div class="b-stat"><span class="tl">Total Trades</span><span class="tv">{{ analysis.backtest_results?.total_trades }}</span></div>
                      <div class="b-stat"><span class="tl">Profit Factor</span><span class="tv">{{ analysis.backtest_results?.profit_factor }}</span></div>
                      <div class="b-stat"><span class="tl">Avg Win</span><span class="tv bullish">+{{ analysis.backtest_results?.avg_win?.toFixed(1) }}%</span></div>
                      <div class="b-stat"><span class="tl">Avg Loss</span><span class="tv bearish">-{{ analysis.backtest_results?.avg_loss?.toFixed(1) }}%</span></div>
                    </div>
                    <!-- Equity Curve Sparkline -->
                    <div class="sparkline-wrap">
                      <svg class="sparkline" viewBox="0 0 200 50" preserveAspectRatio="none">
                        <polyline [attr.points]="getEquityCurvePoints()" class="spark-line" />
                        <polygon [attr.points]="getEquityCurveArea()" class="spark-area" />
                      </svg>
                      <span class="spark-label">Simulated Equity Curve</span>
                    </div>
                  </div>
                </div>

                <div class="section-card chart-card mt-16">
                   <div class="data-header"><span class="icon">📈</span> MARKET DYNAMICS VIEW</div>
                   <div class="chart-box">
                      <button class="btn-load-chart" (click)="toggleChart()" *ngIf="!showChart">🚀 Initialize Intelligence Chart</button>
                      <div class="chart-wrap" *ngIf="showChart">
                        <app-instrument-chart [data]="chartData" [symbol]="analysis.symbol" [overlayLevels]="getChartOverlays()" *ngIf="chartData.length > 0"></app-instrument-chart>
                      </div>
                   </div>
                </div>
              </div>
            </div>


          }
        }
      </div>

      <!-- Journal Modal -->
      @if (showJournalModal) {
        <app-trade-journal [prefill]="journalPrefill" (close)="closeJournalModal()"></app-trade-journal>
      }

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

      <!-- Alert Toast -->
      @if (alertToastVisible) {
        <div class="alert-toast">{{ alertToastMsg }}</div>
      }
    </div>
    </div>
  `,
  styles: [`
    .instrument-view-container { display: flex; flex-direction: column; gap: 16px; }
    .mtf-top-card { width: 100%; border-radius: 12px; }

    .card { background: #0b0b15; border-radius: 12px; padding: 20px; border: 1px solid #1a1a2a; }

    /* Fix Header Layout */
    .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #1f1f3a; }
    .symbol-info { display: flex; flex-direction: column; gap: 4px; }
    .symbol-row { display: flex; align-items: center; gap: 12px; }
    .symbol { font-size: 1.8rem; font-weight: 900; color: #cdd6f4; letter-spacing: 0.5px; }
    .name { font-size: 1rem; color: #9399b2; }
    
    .beta-status, .alpha-status { font-size: 0.65rem; font-weight: 800; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; }
    .beta-status.good { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; border: 1px solid rgba(166, 227, 161, 0.2); }
    .beta-status.bad { background: rgba(243, 139, 168, 0.1); color: #f38ba8; border: 1px solid rgba(243, 139, 168, 0.2); }
    .alpha-status.leader { background: rgba(137, 180, 250, 0.1); color: #89b4fa; border: 1px solid rgba(137, 180, 250, 0.2); }
    .alpha-status.laggard { background: rgba(250, 179, 135, 0.1); color: #fab387; border: 1px solid rgba(250, 179, 135, 0.2); }

    .header-actions-right { display: flex; align-items: center; justify-content: flex-end; gap: 24px; }
    .price-info-block { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
    .price-info { display: flex; align-items: baseline; gap: 12px; }
    .price { font-size: 2rem; font-weight: 900; color: #cdd6f4; line-height: 1; }
    .change { font-size: 1.1rem; font-weight: 800; }
    .change.positive { color: #a6e3a1; }
    .change.negative { color: #f38ba8; }
    .last-updated-row { display: flex; align-items: center; gap: 8px; font-size: 0.75rem; color: #6c7086; font-style: italic; }
    .btn-refresh-local { background: none; border: none; font-size: 0.8rem; cursor: pointer; opacity: 0.7; transition: opacity 0.2s; }
    .btn-refresh-local:hover { opacity: 1; transform: rotate(180deg); }

    /* Tactical Grid Layout */
    .tactical-grid { display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; }

    .section-card { background: #121220; border: 1px solid #1f1f3a; border-radius: 10px; padding: 16px; margin-bottom: 16px; transition: border-color 0.2s; }
    .section-card:hover { border-color: #31315a; }

    /* Strategy Card */
    .strategy-plan-card { border-left: 4px solid #89b4fa; }
    .strategy-plan-card.bullish { border-left-color: #a6e3a1; }
    .strategy-plan-card.bearish { border-left-color: #f38ba8; }
    .card-header-mini { font-size: 0.65rem; color: #9399b2; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
    .plan-hero-text { font-size: 1.4rem; font-weight: 850; color: #cdd6f4; margin-bottom: 8px; }
    .plan-sub-text { font-size: 0.9rem; color: #9399b2; margin-bottom: 16px; line-height: 1.4; }
    .rule-box { background: rgba(137, 180, 250, 0.05); border: 1px dashed rgba(137, 180, 250, 0.2); border-radius: 8px; padding: 12px; display: flex; gap: 10px; margin-top: 10px; }
    .rule-box.scaling { background: rgba(249, 226, 175, 0.05); border-color: rgba(249, 226, 175, 0.2); }
    .rule-text { font-size: 0.85rem; color: #bac2de; }
    .rule-text strong { color: #89b4fa; display: block; font-size: 0.75rem; margin-bottom: 2px; }

    /* Pullback Assessment */
    .pullback-assessment-card { background: rgba(250, 179, 135, 0.03); border: 1px solid rgba(250, 179, 135, 0.1); }
    .pullback-assessment-card.warning { border-color: #f38ba8; background: rgba(243, 139, 168, 0.05); }
    .p-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .p-title { font-size: 0.75rem; font-weight: 800; color: #fab387; }
    .p-score { font-size: 0.75rem; color: #cdd6f4; font-weight: 800; }
    .p-desc { font-size: 0.85rem; color: #9399b2; margin: 0; }

    .btn-chart-link { width: 100%; padding: 14px; background: rgba(137, 180, 250, 0.1); border: 1px solid rgba(137, 180, 250, 0.2); color: #89b4fa; border-radius: 8px; cursor: pointer; font-weight: 700; margin-bottom: 16px; transition: all 0.2s; }
    .btn-chart-link:hover { background: rgba(137, 180, 250, 0.2); border-color: #89b4fa; }

    /* Right Column Badges */
    .signal-score-badge { display: flex; justify-content: space-between; align-items: center; background: #1a1a2e; border: 1px solid #2a2a4a; padding: 14px 20px; border-radius: 40px; margin-bottom: 20px; gap: 16px; min-width: 140px; }
    .signal-score-badge.header-badge { margin-bottom: 0px; padding: 10px 20px; }
    .signal-score-badge.bullish { border-color: #a6e3a1; color: #a6e3a1; }
    .signal-score-badge.bearish { border-color: #f38ba8; color: #f38ba8; }
    .s-label { font-weight: 900; font-size: 1.2rem; }
    .s-score { color: #cdd6f4; font-size: 1rem; }

    /* Data Cards */
    .data-header { font-size: 0.7rem; font-weight: 800; color: #9399b2; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #1f1f3a; padding-bottom: 8px; }
    .data-row-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .data-col { display: flex; flex-direction: column; gap: 4px; }
    .data-col .label { font-size: 0.6rem; color: #6c7086; text-transform: uppercase; }
    .data-col .value { font-size: 1rem; font-weight: 800; color: #cdd6f4; }
    .data-col .value.accent { color: #fab387; }
    .data-col .value.bullish { color: #a6e3a1; }
    .data-col .value.bearish { color: #f38ba8; }
    .sizing-footer { font-size: 0.7rem; color: #6c7086; font-style: italic; margin-top: 12px; }

    /* Economic Context */
    .impact-warning { background: rgba(243, 139, 168, 0.1); border: 1px solid #f38ba8; color: #f38ba8; padding: 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 800; margin-bottom: 12px; }
    .event-stack { display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px; }
    .event-line { font-size: 0.8rem; color: #bac2de; display: flex; align-items: center; gap: 8px; }
    .fund-summary { font-size: 0.8rem; color: #9399b2; line-height: 1.4; margin: 0; }

    /* Trust List */
    .trust-list { list-style: disc; padding-left: 16px; margin: 0; }
    .trust-list li { font-size: 0.8rem; color: #a6adc8; margin-bottom: 4px; }

    /* News Item Row */
    .news-mini-list { display: flex; flex-direction: column; gap: 10px; }
    .news-item-row { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #0b0b15; border: 1px solid #1a1a2a; border-radius: 8px; cursor: pointer; }
    .n-info { display: flex; flex-direction: column; gap: 2px; }
    .n-title { font-size: 0.8rem; color: #cdd6f4; line-height: 1.3; }
    .n-source { font-size: 0.65rem; color: #6c7086; }
    .n-status { font-size: 0.6rem; font-weight: 800; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
    .n-status.bullish { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }
    .n-status.bearish { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }

    /* Inline Metrics */
    .inline-metrics-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    .m-item { background: #121220; padding: 10px; border-radius: 8px; border: 1px solid #1f1f3a; text-align: center; }
    .m-item .l { font-size: 0.6rem; color: #6c7086; display: block; margin-bottom: 4px; }
    .m-item .v { font-size: 0.9rem; font-weight: 800; color: #cdd6f4; }

    /* Insight Layout */
    .insight-top-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .pivot-grid-main { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding-bottom: 12px; }
    .pivot-column { display: flex; flex-direction: column; gap: 8px; }
    .p-item { font-size: 1.05rem; font-weight: 700; color: #cdd6f4; display: flex; gap: 12px; align-items: center; }
    .p-item .t { font-size: 0.75rem; font-weight: 800; padding: 4px 6px; border-radius: 4px; width: 28px; text-align: center; }
    .p-item .t.res { background: rgba(243, 139, 168, 0.15); color: #f38ba8; }
    .p-item .t.sup { background: rgba(166, 227, 161, 0.15); color: #a6e3a1; }
    .pivot-footer { border-top: 1px solid #1f1f3a; padding-top: 8px; display: flex; justify-content: space-between; font-size: 0.7rem; color: #6c7086; }

    .fib-grid-main { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .f-box { background: #0b0b15; border: 1px solid #1a1a2a; padding: 10px; border-radius: 6px; text-align: center; border-bottom: 3px solid #1a1a2a; transition: all 0.2s; }
    .f-box.ext { border-bottom-color: #cba6f7; }
    .f-box.ret { border-bottom-color: #f9e2af; }
    .f-box.high { border-bottom-color: #f38ba8; }
    .f-box.low { border-bottom-color: #a6e3a1; }
    .f-box .l { font-size: 0.6rem; color: #9399b2; text-transform: uppercase; display: block; margin-bottom: 4px; }
    .f-box .v { font-size: 0.95rem; font-weight: 800; color: #cdd6f4; }

    .backtest-layout { display: flex; flex-direction: column; gap: 12px; }
    .backtest-stats-row { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
    .b-stat { display: flex; flex-direction: column; gap: 4px; }
    .b-stat .tl { font-size: 0.7rem; color: #6c7086; }
    .b-stat .tv { font-size: 1.2rem; font-weight: 900; color: #cdd6f4; }
    .b-stat .tv.highlight { color: #a6e3a1; }
    .b-stat .tv.bullish { color: #a6e3a1; font-size: 0.95rem; }
    .b-stat .tv.bearish { color: #f38ba8; font-size: 0.95rem; }

    /* Equity Sparkline */
    .sparkline-wrap { display: flex; flex-direction: column; gap: 4px; }
    .sparkline { width: 100%; height: 50px; display: block; }
    .spark-line { fill: none; stroke: #a6e3a1; stroke-width: 1.5; }
    .spark-area { fill: rgba(166,227,161,0.1); stroke: none; }
    .spark-label { font-size: 0.6rem; color: #6c7086; text-align: right; font-style: italic; }

    /* Candle Pattern Badge */
    .candle-badge { font-size: 0.6rem; font-weight: 800; padding: 3px 8px; border-radius: 4px; text-transform: uppercase; white-space: nowrap; }
    .candle-badge.bull { background: rgba(166,227,161,0.1); color: #a6e3a1; border: 1px solid rgba(166,227,161,0.25); }
    .candle-badge.bear { background: rgba(243,139,168,0.1); color: #f38ba8; border: 1px solid rgba(243,139,168,0.25); }
    .candle-badge.neutral { background: rgba(249,226,175,0.1); color: #f9e2af; border: 1px solid rgba(249,226,175,0.25); }

    /* Strategy Mode Toggle */
    .strategy-mode-toggle { display: flex; gap: 4px; margin-left: auto; }
    .sm-btn { background: transparent; border: 1px solid #2a2a4a; color: #6c7086; font-size: 0.65rem; font-weight: 800; padding: 4px 10px; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
    .sm-btn.active { background: rgba(137,180,250,0.1); border-color: #89b4fa; color: #89b4fa; }

    /* Action Button Row */
    .action-btn-row { display: flex; gap: 8px; margin-bottom: 16px; }
    .btn-chart-link { flex: 1; padding: 12px; background: rgba(137,180,250,0.1); border: 1px solid rgba(137,180,250,0.2); color: #89b4fa; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 0.85rem; transition: all 0.2s; }
    .btn-chart-link:hover { background: rgba(137,180,250,0.2); }
    .btn-journal { flex: 1; padding: 12px; background: rgba(166,227,161,0.08); border: 1px solid rgba(166,227,161,0.2); color: #a6e3a1; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 0.85rem; transition: all 0.2s; }
    .btn-journal:hover { background: rgba(166,227,161,0.15); }

    /* Bell Buttons on Pivot Levels */
    .bell-btn { background: none; border: none; cursor: pointer; font-size: 0.7rem; opacity: 0.3; margin-left: auto; padding: 0 2px; transition: opacity 0.2s, transform 0.2s; }
    .p-item:hover .bell-btn { opacity: 1; }
    .bell-btn:hover { transform: scale(1.3); }
    .bell-btn.active { opacity: 1; filter: drop-shadow(0 0 3px #f9e2af); }

    /* Alert Toast */
    .alert-toast { position: fixed; bottom: 24px; right: 24px; background: #1e1e2e; border: 1px solid #89b4fa; border-radius: 10px; padding: 12px 18px; color: #cdd6f4; font-size: 0.85rem; z-index: 9999; display: flex; align-items: center; gap: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); animation: slide-up 0.3s ease; }
    @keyframes slide-up { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }

    @media (max-width: 900px) { .tactical-grid { grid-template-columns: 1fr; } }
  `]
})
export class InstrumentCardComponent implements OnChanges {
  @Input() analysis!: InstrumentAnalysis;
  @Output() refresh = new EventEmitter<string>();
  @Output() modeChange = new EventEmitter<'long_term' | 'short_term'>();

  private marketAnalyzerService = inject(MarketAnalyzerService);

  selectedTab: 'plan' | 'insight' = 'plan';
  showChart = false;
  isLoadingChart = false;
  chartData: ChartData[] = [];
  selectedNewsItem: NewsItem | null = null;
  showJournalModal = false;
  journalPrefill: any = null;
  alertToastMsg = '';
  alertToastVisible = false;
  activeLevelAlerts = new Set<string>();

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

  switchMode(mode: 'long_term' | 'short_term') {
    if (this.analysis.strategy_mode === mode) return; // already active, skip
    this.modeChange.emit(mode);
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

  // ── Journal Modal ────────────────────────────────────────────────────────────
  openJournalModal() {
    const a = this.analysis;
    const direction = a.trade_signal.recommendation === 'bearish' ? 'short' : 'long';
    this.journalPrefill = {
      symbol: a.symbol,
      direction,
      entry_price: a.position_sizing?.entry_price ?? a.current_price,
      size: a.position_sizing?.suggested_units ?? null,
      notes: `${a.trade_signal.action_plan}. Score: ${a.trade_signal.score}. ${a.trade_signal.action_plan_details}`,
      date: new Date().toISOString().slice(0, 10),
    };
    this.showJournalModal = true;
  }

  closeJournalModal() {
    this.showJournalModal = false;
    this.journalPrefill = null;
  }

  // ── Smart Level Alerts (local toast + localStorage) ──────────────────────────
  addLevelAlert(key: string, price: number) {
    const stored = JSON.parse(localStorage.getItem('market_level_alerts') || '[]');
    const exists = stored.some((a: any) => a.key === key && a.symbol === this.analysis.symbol);
    if (exists) {
      // Remove if already exists (toggle off)
      const updated = stored.filter((a: any) => !(a.key === key && a.symbol === this.analysis.symbol));
      localStorage.setItem('market_level_alerts', JSON.stringify(updated));
      this.activeLevelAlerts.delete(`${this.analysis.symbol}_${key}`);
      this.showToast(`🔕 Alert removed for $${price.toFixed(2)}`);
    } else {
      stored.push({ key, symbol: this.analysis.symbol, price, createdAt: new Date().toISOString() });
      localStorage.setItem('market_level_alerts', JSON.stringify(stored));
      this.activeLevelAlerts.add(`${this.analysis.symbol}_${key}`);
      this.showToast(`🔔 Alert set: ${this.analysis.symbol} @ $${price.toFixed(2)}`);
    }
  }

  isAlertActive(key: string): boolean {
    return this.activeLevelAlerts.has(`${this.analysis.symbol}_${key}`);
  }

  private showToast(msg: string) {
    this.alertToastMsg = msg;
    this.alertToastVisible = true;
    setTimeout(() => { this.alertToastVisible = false; }, 3000);
  }

  // ── Chart Overlays ────────────────────────────────────────────────────────────
  getChartOverlays(): import('../instrument-chart/instrument-chart.component').ChartOverlayLevel[] {
    const a = this.analysis;
    const overlays: import('../instrument-chart/instrument-chart.component').ChartOverlayLevel[] = [];

    if (a.technical_indicators) {
      const pp = a.technical_indicators.pivot_points;
      overlays.push(
        { price: pp.r1, label: 'R1', color: 'rgba(243,139,168,0.7)', lineStyle: 2 },
        { price: pp.r2, label: 'R2', color: 'rgba(243,139,168,0.5)', lineStyle: 2 },
        { price: pp.r3, label: 'R3', color: 'rgba(243,139,168,0.3)', lineStyle: 2 },
        { price: pp.s1, label: 'S1', color: 'rgba(166,227,161,0.7)', lineStyle: 2 },
        { price: pp.s2, label: 'S2', color: 'rgba(166,227,161,0.5)', lineStyle: 2 },
        { price: pp.s3, label: 'S3', color: 'rgba(166,227,161,0.3)', lineStyle: 2 },
        { price: pp.pivot, label: 'Pivot', color: 'rgba(137,180,250,0.6)', lineStyle: 1 },
      );

      const fib = a.technical_indicators.fibonacci;
      if (fib) {
        overlays.push(
          { price: fib.ret_382, label: 'Ret 38.2%', color: 'rgba(249,226,175,0.6)', lineStyle: 3 },
          { price: fib.ret_618, label: 'Ret 61.8%', color: 'rgba(249,226,175,0.8)', lineStyle: 3 },
          { price: fib.ext_1272, label: 'Ext 1.272', color: 'rgba(203,166,247,0.6)', lineStyle: 3 },
        );
      }
    }

    if (a.volatility_risk) {
      overlays.push(
        { price: a.volatility_risk.stop_loss, label: 'SL', color: 'rgba(243,139,168,0.9)', lineStyle: 0 },
        { price: a.volatility_risk.take_profit, label: 'TP', color: 'rgba(166,227,161,0.9)', lineStyle: 0 },
      );
    }

    return overlays;
  }

  // ── Equity Curve Sparkline ────────────────────────────────────────────────────
  getEquityCurvePoints(): string {
    return this.generateCurve(false);
  }

  getEquityCurveArea(): string {
    return this.generateCurve(true);
  }

  private generateCurve(asArea: boolean): string {
    const bt = this.analysis.backtest_results;
    if (!bt) return '';
    // Simulate an equity curve from backtest stats
    const n = 20;
    const winRate = (bt.win_rate || 50) / 100;
    const avgWin = bt.avg_win || 1;
    const avgLoss = bt.avg_loss || 1;
    let equity = 100;
    const points: number[] = [equity];
    for (let i = 1; i < n; i++) {
      const win = Math.random() < winRate;
      equity += win ? (avgWin / 2) : -(avgLoss / 2);
      points.push(equity);
    }
    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1;
    const mapped = points.map((v, i) => {
      const x = (i / (n - 1)) * 200;
      const y = 50 - ((v - min) / range) * 45;
      return `${x},${y}`;
    });
    if (asArea) {
      return `${mapped.join(' ')} 200,50 0,50`;
    }
    return mapped.join(' ');
  }
}

