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
    <div class="instrument-terminal">
      <!-- 1. MTF TOP BANNER -->
      <div class="terminal-banner">
        <app-multi-timeframe-overlay [analysis]="analysis"></app-multi-timeframe-overlay>
      </div>

      <div class="terminal-body" [class]="getCardClass()">
        <!-- 2. SMART HUD HEADER (COMPACT) -->
        <header class="terminal-header">
          <div class="th-left">
            <div class="th-symbol-row">
              <span class="th-symbol">{{ analysis.symbol }}</span>
              <div class="th-price-stack">
                <span class="th-price">\${{ analysis.current_price.toFixed(2) }}</span>
                <span class="th-change" [class]="getPriceChangeClass()">
                  {{ analysis.daily_strength.price_change_percent > 0 ? '+' : '' }}{{ analysis.daily_strength.price_change_percent.toFixed(2) }}%
                </span>
              </div>
            </div>
            <div class="th-badges">
              <span class="th-badge strategy" [class]="analysis.strategy_mode">
                {{ analysis.strategy_mode === 'long_term' ? '📈' : '⚡' }}
              </span>
              <div class="th-clocks">
                <span class="th-clock session" [class]="getCurrentSession().toLowerCase().replace(' ', '-')">{{ getCurrentSession() }}</span>
                <span class="th-clock event" [class.impact]="analysis.fundamentals?.has_high_impact_events">{{ getNextEvent() }}</span>
              </div>
            </div>
          </div>

          <div class="th-right-compact">
            <div class="th-status-pill" [class]="getSignalClass()">
               <span class="th-s-val">{{ analysis.trade_signal.score }}</span>
               <span class="th-s-rec">{{ analysis.trade_signal.recommendation }}</span>
            </div>
            <button class="btn-refresh-circle" (click)="onRefresh()">🔄</button>
          </div>
        </header>

        <!-- 3. DECISION TILES (BALANCED PRO GRID) -->
        <div class="terminal-grid">
          
          <!-- EXPERT BATTLE PLAN (RESTORED WIDTH) -->
          @if (analysis.expert_trade_plan) {
            <section class="t-tile expert-tile" [class.high-intent]="analysis.expert_trade_plan.is_high_intent">
              <div class="tile-header">🎖️ EXPERT BATTLE PLAN</div>
              <div class="expert-main">
                <div class="expert-plan-text">{{ analysis.expert_trade_plan.battle_plan }}</div>
                <div class="expert-badges">
                  <div class="expert-badge rvol">
                    <span class="eb-v">{{ analysis.expert_trade_plan.rvol }}x</span>
                    <span class="eb-l">VOL</span>
                  </div>
                  @if (analysis.expert_trade_plan.is_high_intent) {
                    <div class="expert-badge intent pulse">🔥 HIGH INTENT</div>
                  }
                </div>
              </div>
            </section>
          }
          
          <!-- CORE STRATEGIC ACTION (RESTORED PANELS) -->
          <section class="t-tile action-tile">
            <div class="tile-header">🎯 STRATEGIC ACTION</div>
            <div class="action-hero">
               <div class="aph-text">{{ analysis.trade_signal.action_plan }}</div>
               <div class="aph-sub">{{ analysis.trade_signal.action_plan_details }}</div>
            </div>
            
            <div class="levels-stack">
              <div class="lvl-box entry">
                <span class="ll">ENTRY ZONE</span>
                <span class="lv">\${{ getEntryZone() }}</span>
              </div>
              <div class="lvl-box sl">
                <span class="ll">STOP LOSS</span>
                <span class="lv bearish">\${{ analysis.volatility_risk.stop_loss.toFixed(2) }}</span>
              </div>
              <div class="lvl-box tp">
                <span class="ll">TAKE PROFIT (Target)</span>
                <span class="lv bullish">\${{ analysis.volatility_risk.take_profit.toFixed(2) }}</span>
              </div>
            </div>

            <!-- Price Gauge -->
            <div class="terminal-gauge">
               <div class="tg-labels"><span>S3</span><span>S1</span><span>PIVOT</span><span>R1</span><span>R3</span></div>
               <div class="tg-track">
                  <div class="tg-fill" [style.left.%]="getPricePositionPercent()"></div>
                  <div class="tg-marker pivot" style="left: 50%"></div>
               </div>
               <div class="tg-footer">Distance to VWAP: <strong [class]="getVWAPClass()">{{ analysis.daily_strength.vwap_dist_pct?.toFixed(2) }}%</strong></div>
            </div>

            <!-- Position Calculator -->
            <div class="position-calculator">
               <div class="pc-header">🧮 RISK CALCULATOR</div>
               <div class="pc-toggles">
                  <button (click)="riskMultiplier = 0.5" [class.active]="riskMultiplier === 0.5">0.5%</button>
                  <button (click)="riskMultiplier = 1.0" [class.active]="riskMultiplier === 1.0">1.0%</button>
                  <button (click)="riskMultiplier = 2.0" [class.active]="riskMultiplier === 2.0">2.0%</button>
               </div>
               <div class="pc-result">
                  <div class="pcr-item"><span>LOTS/UNITS</span><strong>{{ getCalculatedLotSize() }}</strong></div>
                  <div class="pcr-item"><span>RISK $</span><strong>{{ getRiskAmount() }}</strong></div>
               </div>
            </div>

            <!-- Percentage Scaling Plan -->
            <div class="scaling-plan">
              <div class="sp-header">⚖️ PERCENTAGE SCALING PLAN (50 / 30 / 20)</div>
              <div class="sp-grid">
                @for (step of getScalingStrategy(); track step.stage) {
                  <div class="sp-step">
                    <span class="sps-p">{{ step.percent }}%</span>
                    <div class="sps-details">
                      <span class="sps-l">{{ step.stage }}</span>
                      <strong class="sps-v">{{ step.target }}</strong>
                    </div>
                  </div>
                }
              </div>
            </div>

            <div class="tile-actions">
              <button class="btn-primary" (click)="openJournalModal()">📒 Log Trade</button>
              <button class="btn-secondary" (click)="toggleChart()">📊 View Chart</button>
            </div>
          </section>

          <!-- VALIDATION & CONTEXT (RESTORED LABELS) -->
          <section class="t-tile status-tile">
            <div class="tile-header">🛡️ VALIDATION & CONTEXT</div>
            <div class="checklist-compact-full">
              <div class="ch-item" [class]="getTrendCheck()"><span class="ch-i">Trend</span><span class="ch-v">{{ analysis.monthly_trend.direction | uppercase }}</span></div>
              <div class="ch-item" [class]="getMomentumCheck()"><span class="ch-i">Momentum</span><span class="ch-v">{{ analysis.daily_strength.adx.toFixed(0) }}</span></div>
              <div class="ch-item" [class]="getVolumeCheck()"><span class="ch-i">Volume</span><span class="ch-v">{{ analysis.daily_strength.volume_ratio.toFixed(1) }}x</span></div>
              <div class="ch-item" [class]="getRSICheck()"><span class="ch-i">RSI</span><span class="ch-v">{{ analysis.daily_strength.rsi.toFixed(0) }}</span></div>
              <div class="ch-item" [class]="getBetaCheck()"><span class="ch-i">Beta</span><span class="ch-v">{{ analysis.benchmark_direction | uppercase }}</span></div>
              <div class="ch-item" [class]="getPullbackCheck()"><span class="ch-i">Risk Score</span><span class="ch-v">{{ analysis.pullback_warning?.warning_score || 0 }}/8</span></div>
            </div>

            <div class="verdict-banner-pro" [class]="getOverallCheckClass()">
                {{ analysis.trade_signal.score * 10 }}. Score {{ analysis.trade_signal.score * 10 }}.
            </div>

            @if (analysis.intermarket_context) {
              <div class="intermarket-mini">
                  <div class="im-header">INTERMARKET TAILWINDS</div>
                  <div class="im-summary" [class]="analysis.intermarket_context.gold_implication">
                    {{ analysis.intermarket_context.description }}
                  </div>
              </div>
            }

            <div class="probability-mini">
              <div class="prob-header">PROBABILITY DEPTH</div>
              <div class="bt-stats">
                <div class="bt-s"><span>WIN RATE</span><strong>{{ analysis.backtest_results?.win_rate?.toFixed(1) }}%</strong></div>
                <div class="bt-s"><span>PF</span><strong>{{ analysis.backtest_results?.profit_factor }}</strong></div>
              </div>
              <div class="bt-chart">
                <svg viewBox="0 0 200 40" preserveAspectRatio="none">
                  <polyline [attr.points]="getEquityCurvePoints()" class="spark-line" />
                </svg>
              </div>
            </div>
            
            <div class="intel-expander-v2">
               <button class="exp-btn-v2" (click)="showMoreIntel = !showMoreIntel">
                  {{ showMoreIntel ? '📂 Hide Metrics' : '📁 Show More Intelligence' }}
               </button>
            </div>
          </section>
        </div>

        <!-- COLLAPSIBLE DEEP DATA -->
        <div class="deep-data-section" *ngIf="showMoreIntel">
           <div class="deep-grid">
              <div class="deep-card news">
                <div class="dc-header">NEWS INTELLIGENCE</div>
                <div class="mini-news-stack">
                  @for (item of analysis.news_sentiment?.news_items?.slice(0, 3); track item.title) {
                    <div class="mn-item" (click)="openNewsModal(item)">
                       <span class="mn-t">{{ item.title }}</span>
                       <span class="mn-s" [class]="item.sentiment_label.toLowerCase()">{{ item.sentiment_label }}</span>
                    </div>
                  }
                </div>
              </div>
              <div class="deep-card pivots">
                 <div class="dc-header">PIVOT MATRIX / EXTENSIONS</div>
                 <div class="pm-grid">
                    <div class="pm-v res">R3: \${{ analysis.technical_indicators?.pivot_points?.r3 }}</div>
                    <div class="pm-v res">R2: \${{ analysis.technical_indicators?.pivot_points?.r2 }}</div>
                    <div class="pm-v res">R1: \${{ analysis.technical_indicators?.pivot_points?.r1 }}</div>
                    <div class="pm-v center">P: \${{ analysis.technical_indicators?.pivot_points?.pivot }}</div>
                    <div class="pm-v sup">S1: \${{ analysis.technical_indicators?.pivot_points?.s1 }}</div>
                    <div class="pm-v sup">S2: \${{ analysis.technical_indicators?.pivot_points?.s2 }}</div>
                    <div class="pm-v sup">S3: \${{ analysis.technical_indicators?.pivot_points?.s3 }}</div>
                 </div>
                 <div class="fib-ext-belt">
                    <div class="feb-item"><span>1.272 Ext</span><strong>\${{ analysis.technical_indicators?.fibonacci?.ext_1272 }}</strong></div>
                    <div class="feb-item"><span>1.618 Ext</span><strong>\${{ analysis.technical_indicators?.fibonacci?.ext_1618 }}</strong></div>
                 </div>
              </div>
           </div>
        </div>

        <!-- Inline Chart Area -->
        <div class="terminal-chart-area" *ngIf="showChart">
           <app-instrument-chart [data]="chartData" [symbol]="analysis.symbol" [overlayLevels]="getChartOverlays()" *ngIf="chartData.length > 0"></app-instrument-chart>
        </div>
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
  `,
  styles: [`
    :host { display: block; width: 100%; margin-bottom: 30px; }
    .instrument-terminal { background: #0b0b15; border-radius: 16px; border: 1px solid #1a1a2a; overflow: hidden; }
    
    .terminal-banner { width: 100%; }
    
    .terminal-body { padding: 0; }
    .terminal-body.bullish { border-left: 3px solid #a6e3a1; }
    .terminal-body.bearish { border-left: 3px solid #f38ba8; }

    /* HUD UPGRADE (ZERO WASTE) */
    .terminal-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 12px 16px; background: #0b0b15; border-bottom: 1px solid #1f1f3a; }
    .th-symbol-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .th-symbol { font-size: 1.4rem; font-weight: 950; color: #cdd6f4; }
    .th-price-stack { display: flex; gap: 8px; align-items: baseline; }
    .th-price { font-size: 1.1rem; font-weight: 900; color: #bac2de; }
    .th-change { font-size: 0.8rem; font-weight: 800; }
    .th-badges { display: flex; gap: 6px; align-items: center; }
    .th-clock { font-size: 0.5rem; padding: 1px 4px; }
    
    .th-right-compact { display: flex; align-items: center; gap: 12px; }
    .th-status-pill { padding: 4px 10px; border-radius: 4px; display: flex; align-items: center; gap: 8px; border: 1px solid; }
    .th-status-pill.bullish { border-color: #a6e3a1; color: #a6e3a1; background: rgba(166, 227, 161, 0.1); }
    .th-status-pill.bearish { border-color: #f38ba8; color: #f38ba8; background: rgba(243, 139, 168, 0.1); }
    .btn-refresh-circle { background: #1a1a2a; border: 1px solid #313244; color: #6c7086; padding: 6px; border-radius: 50%; cursor: pointer; }

    /* 3. DECISION TILES (PRO RESTORATION) */
    .terminal-grid { display: grid; grid-template-columns: 1.2fr 1.1fr 0.9fr; gap: 0; background: #0b0b15; }
    .t-tile { padding: 20px; border-right: 1px solid #1f1f3a; border-bottom: 1px solid #1f1f3a; }
    .tile-header { font-size: 0.65rem; font-weight: 950; color: #45475a; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px; }

    /* EXPERT PANEL RESTORED */
    .expert-tile { background: linear-gradient(135deg, rgba(137, 180, 250, 0.03), transparent); }
    .expert-tile.high-intent { border-top: 3px solid #fab387; background: rgba(250, 179, 135, 0.05); }
    .expert-main { display: flex; flex-direction: column; gap: 16px; }
    .expert-plan-text { font-size: 1.1rem; color: #cdd6f4; line-height: 1.4; font-weight: 500; }
    .expert-badges { display: flex; gap: 8px; }
    .expert-badge { padding: 4px 10px; border-radius: 4px; background: #1a1a2a; border: 1px solid #313244; display: flex; gap: 8px; align-items: center; }
    .eb-v { font-size: 0.85rem; font-weight: 950; color: #89b4fa; }
    .eb-l { font-size: 0.55rem; color: #45475a; font-weight: 800; }
    .intent.pulse { color: #fab387; border-color: #fab387; font-size: 0.65rem; font-weight: 900; animation: glow 2s infinite; }
    @keyframes glow { 0%, 100% { box-shadow: 0 0 5px rgba(250, 179, 135, 0.2); } 50% { box-shadow: 0 0 15px rgba(250, 179, 135, 0.4); } }

    /* ACTION PANEL RESTORED */
    .action-hero { margin-bottom: 24px; }
    .aph-text { font-size: 1.3rem; font-weight: 900; color: #cdd6f4; margin-bottom: 6px; }
    .aph-sub { font-size: 0.85rem; color: #6c7086; line-height: 1.4; }
    
    .levels-stack { display: flex; gap: 10px; margin-bottom: 24px; }
    .lvl-box { flex: 1; padding: 12px; border-radius: 8px; background: #11111b; border: 1px solid #1f1f3a; display: flex; flex-direction: column; gap: 4px; }
    .ll { font-size: 0.45rem; color: #45475a; font-weight: 950; text-transform: uppercase; }
    .lv { font-size: 0.95rem; font-weight: 950; color: #cdd6f4; }
    .lv.bullish { color: #a6e3a1; }
    .lv.bearish { color: #f38ba8; }

    /* PRICE GAUGE RESTORED */
    .terminal-gauge { margin-bottom: 24px; background: rgba(30, 30, 46, 0.2); padding: 12px; border-radius: 8px; }
    .tg-labels { display: flex; justify-content: space-between; font-size: 0.5rem; color: #313244; font-weight: 950; margin-bottom: 6px; }
    .tg-track { height: 4px; background: #1a1a2a; border-radius: 2px; position: relative; }
    .tg-fill { width: 10px; height: 10px; border-radius: 50%; background: #cdd6f4; position: absolute; top: 50%; transform: translate(-50%, -50%); border: 2px solid #11111b; box-shadow: 0 0 8px #cdd6f4; transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    .tg-marker.pivot { width: 1px; height: 10px; background: #89b4fa; position: absolute; top: -3px; }

    /* RISK CALCULATOR RESTORED */
    .position-calculator { background: #11111b; border: 1px solid #1f1f3a; border-radius: 8px; padding: 16px; margin-bottom: 24px; }
    .pc-header { font-size: 0.55rem; color: #45475a; font-weight: 950; margin-bottom: 12px; }
    .pc-toggles { display: flex; gap: 6px; margin-bottom: 16px; }
    .pc-toggles button { flex: 1; background: #1e1e2e; border: 1px solid #313244; color: #6c7086; padding: 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 900; cursor: pointer; }
    .pc-toggles button.active { background: #89b4fa; color: #11111b; border-color: #89b4fa; }
    .pc-result { display: flex; justify-content: space-between; }
    .pcr-item { display: flex; flex-direction: column; }
    .pcr-item span { font-size: 0.45rem; color: #45475a; font-weight: 950; }
    .pcr-item strong { font-size: 1.1rem; font-weight: 950; color: #cdd6f4; }

    /* SCALING PLAN RESTORED */
    .scaling-plan { background: rgba(137, 180, 250, 0.03); border: 1px dashed rgba(137, 180, 250, 0.2); border-radius: 8px; padding: 16px; margin-bottom: 24px; }
    .sp-header { font-size: 0.55rem; color: #89b4fa; font-weight: 950; margin-bottom: 12px; }
    .sp-grid { display: flex; flex-direction: column; gap: 10px; }
    .sp-step { display: flex; justify-content: space-between; align-items: center; }
    .sps-p { font-size: 0.9rem; font-weight: 950; color: #89b4fa; }
    .sps-l { font-size: 0.65rem; color: #9399b2; font-weight: 700; }
    .sps-v { font-size: 0.85rem; color: #cdd6f4; font-weight: 950; }

    .tile-actions { display: flex; gap: 12px; }
    .btn-primary { flex: 1.2; padding: 14px; background: #89b4fa; border: none; border-radius: 8px; color: #11111b; font-weight: 900; font-size: 0.9rem; cursor: pointer; position: relative; overflow: hidden; }
    .btn-secondary { flex: 1; padding: 14px; background: transparent; border: 1px solid #313244; border-radius: 8px; color: #89b4fa; font-weight: 900; font-size: 0.9rem; cursor: pointer; }

    /* VALIDATION PANEL RESTORED */
    .checklist-compact-full { display: grid; grid-template-columns: 1fr; gap: 8px; margin-bottom: 20px; }
    .ch-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; background: #121220; border-radius: 6px; border: 1px solid #1f1f3a; transition: transform 0.2s; }
    .ch-item.pass { border-left: 3px solid #a6e3a1; }
    .ch-item.warn { border-left: 3px solid #f9e2af; }
    .ch-item.fail { border-left: 3px solid #f38ba8; }
    .ch-i { font-size: 0.65rem; font-weight: 800; color: #585b70; text-transform: uppercase; }
    .ch-v { font-size: 0.8rem; font-weight: 950; color: #cdd6f4; }

    .verdict-banner-pro { width: 100%; padding: 16px; border-radius: 8px; text-align: center; font-size: 0.9rem; font-weight: 950; margin-bottom: 24px; }
    .verdict-banner-pro.go { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; border: 1px solid #a6e3a1; }
    .verdict-banner-pro.caution { background: rgba(249, 226, 175, 0.1); color: #f9e2af; border: 1px solid #f9e2af; }
    .verdict-banner-pro.no-go { background: rgba(243, 139, 168, 0.1); color: #f38ba8; border: 1px solid #f38ba8; }

    .probability-mini { padding-top: 20px; border-top: 1px solid #1f1f3a; margin-bottom: 24px; }
    .prob-header { font-size: 0.55rem; color: #45475a; font-weight: 950; margin-bottom: 16px; }
    .bt-stats { display: flex; justify-content: space-between; margin-bottom: 12px; }
    .bt-s { display: flex; flex-direction: column; }
    .bt-s span { font-size: 0.45rem; color: #45475a; }
    .bt-s strong { font-size: 1.2rem; font-weight: 950; color: #cdd6f4; }
    .bt-chart { width: 100%; height: 40px; }
    .spark-line { fill: none; stroke: #a6e3a1; stroke-width: 2; }

    .intel-expander-v2 { text-align: center; }
    .exp-btn-v2 { width: 100%; padding: 12px; background: #1a1a2a; border: 1px dashed #313244; color: #6c7086; border-radius: 8px; font-weight: 900; font-size: 0.75rem; cursor: pointer; }

    /* MOBILE BREAKPOINT RESTORED */
    @media (max-width: 768px) {
      .terminal-grid { grid-template-columns: 1fr; }
      .t-tile { border-right: none; }
      .levels-stack { flex-direction: column; }
    }

    /* DEEP DATA SECTION */
    .deep-data-section { padding: 24px; background: rgba(17, 17, 27, 0.5); border-bottom: 1px solid #1f1f3a; }
    .deep-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    .dc-header { font-size: 0.6rem; color: #45475a; font-weight: 900; margin-bottom: 12px; }
    
    .mn-item { display: flex; justify-content: space-between; align-items: center; padding: 10px; background: #0b0b15; border: 1px solid #1f1f3a; border-radius: 6px; cursor: pointer; margin-bottom: 8px; }
    .mn-t { font-size: 0.75rem; color: #cdd6f4; }
    .mn-s { font-size: 0.55rem; font-weight: 900; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; }
    .mn-s.bullish { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }
    .mn-s.bearish { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }

    .pm-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
    .pm-v { font-size: 0.7rem; font-weight: 800; color: #bac2de; padding: 6px; background: #0b0b15; border-radius: 4px; text-align: center; }
    .pm-v.res { color: #f38ba8; }
    .pm-v.sup { color: #a6e3a1; }
    .pm-v.center { background: rgba(137, 180, 250, 0.1); border: 1px solid #89b4fa; }

    .terminal-chart-area { padding: 24px; background: #000; height: 400px; }

    
    /* HUD CLOCKS */
    .th-clocks { display: flex; gap: 8px; margin-left: 12px; }
    .th-clock { font-size: 0.55rem; font-weight: 900; padding: 2px 6px; border-radius: 4px; background: #1a1a2a; border: 1px solid #313244; color: #6c7086; }
    .th-clock.london { color: #89b4fa; border-color: #89b4fa; }
    .th-clock.new-york { color: #f9e2af; border-color: #f9e2af; }
    .th-clock.asia { color: #a6e3a1; border-color: #a6e3a1; }
    .th-clock.transition { color: #585b70; border-color: #585b70; }
    .th-clock.event.impact { color: #f38ba8; border-color: #f38ba8; animation: blink 1s infinite; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }

    .th-state-hud { display: flex; gap: 8px; margin-top: 10px; }
    .state-label { font-size: 0.55rem; font-weight: 800; padding: 2px 8px; border-radius: 100px; background: rgba(49, 50, 68, 0.4); border: 1px solid #1f1f3a; color: #9399b2; text-transform: uppercase; }
    .state-label.bullish { color: #a6e3a1; border-color: rgba(166, 227, 161, 0.3); background: rgba(166, 227, 161, 0.05); }
    .state-label.bearish { color: #f38ba8; border-color: rgba(243, 139, 168, 0.3); background: rgba(243, 139, 168, 0.05); }
    .state-label.neutral { color: #f9e2af; border-color: rgba(249, 226, 175, 0.3); background: rgba(249, 226, 175, 0.05); }

    /* POSITION CALCULATOR */
    .position-calculator { background: #11111b; border: 1px solid #1f1f3a; border-radius: 8px; padding: 12px; margin-bottom: 24px; }
    .pc-header { font-size: 0.55rem; color: #45475a; font-weight: 950; margin-bottom: 10px; }
    .pc-toggles { display: flex; gap: 4px; margin-bottom: 12px; }
    .pc-toggles button { flex: 1; background: #1e1e2e; border: 1px solid #313244; color: #bac2de; font-size: 0.65rem; font-weight: 800; padding: 6px; border-radius: 4px; cursor: pointer; }
    .pc-toggles button.active { background: #89b4fa; color: #11111b; border-color: #89b4fa; }
    .pc-result { display: flex; justify-content: space-between; gap: 12px; }
    .pcr-item { flex: 1; display: flex; flex-direction: column; }
    .pcr-item span { font-size: 0.45rem; color: #45475a; font-weight: 900; }
    .pcr-item strong { font-size: 0.95rem; color: #cdd6f4; font-weight: 950; }

    .correlation-warning { font-size: 0.65rem; color: #f9e2af; background: rgba(249, 226, 175, 0.05); padding: 8px; border-radius: 4px; border: 1px dashed rgba(249, 226, 175, 0.3); margin-bottom: 12px; }

    /* TH REGIME */
    .th-regime { display: flex; align-items: center; gap: 4px; font-size: 0.55rem; font-weight: 800; color: #6c7086; margin-left: 12px; }
    .th-regime.bullish .regime-value { color: #a6e3a1; }
    .th-regime.bearish .regime-value { color: #f38ba8; }

    /* SCALING PLAN */
    .scaling-plan { background: rgba(137, 180, 250, 0.05); border: 1px dashed rgba(137, 180, 250, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 24px; }
    .sp-header { font-size: 0.55rem; color: #89b4fa; font-weight: 950; margin-bottom: 10px; }
    .sp-grid { display: flex; flex-direction: column; gap: 8px; }
    .sp-step { display: flex; align-items: center; gap: 12px; }
    .sps-p { font-size: 0.8rem; font-weight: 950; color: #89b4fa; min-width: 35px; }
    .sps-details { flex: 1; display: flex; justify-content: space-between; align-items: center; }
    .sps-l { font-size: 0.6rem; color: #9399b2; font-weight: 700; }
    .sps-v { font-size: 0.75rem; color: #cdd6f4; font-weight: 900; }

    /* PULLBACK ALERTS */
    .pullback-alerts { margin-top: 12px; display: flex; flex-direction: column; gap: 4px; }
    .pa-item { font-size: 0.65rem; color: #fab387; background: rgba(250, 179, 135, 0.05); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(250, 179, 135, 0.2); }

    /* FIB EXT */
    .fib-ext-belt { display: flex; gap: 12px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #1f1f3a; }
    .feb-item { flex: 1; display: flex; flex-direction: column; }
    .feb-item span { font-size: 0.5rem; color: #45475a; font-weight: 900; text-transform: uppercase; }
    .feb-item strong { font-size: 0.75rem; color: #cba6f7; font-weight: 950; }

    /* RESPONSIVE */
    @media (max-width: 1100px) {
      .terminal-grid { grid-template-columns: 1fr 1fr; }
      .insight-tile { grid-column: span 2; border-right: none; border-top: 1px solid #1f1f3a; }
    }

    @media (max-width: 768px) {
      .terminal-header { flex-direction: column; align-items: flex-start; gap: 20px; }
      .th-right { width: 100%; justify-content: space-between; }
      .terminal-grid { grid-template-columns: 1fr; }
      .t-tile { border-right: none; border-bottom: 1px solid #1f1f3a; }
      .insight-tile { grid-column: span 1; }
      .th-metrics { display: none; }
      .th-symbol { font-size: 1.5rem; }
      .aph-text { font-size: 1.2rem; }
      .lvl-box { padding: 6px; }
      .lv { font-size: 0.8rem; }
      .deep-grid { grid-template-columns: 1fr; }
    }

    @keyframes pulse { 0% { opacity: 0.8; } 50% { opacity: 1; } 100% { opacity: 0.8; } }
  `]
})
export class InstrumentCardComponent implements OnChanges {
  riskMultiplier = 1.0;

  getCalculatedLotSize(): string {
    if (!this.analysis.position_sizing) return 'N/A';
    // Base units from backend are for 1% risk. Adjust locally.
    const units = this.analysis.position_sizing.suggested_units * this.riskMultiplier;
    return units.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  getRiskAmount(): string {
    if (!this.analysis.position_sizing) return 'N/A';
    const amount = this.analysis.position_sizing.risk_amount * this.riskMultiplier;
    return amount.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
  }

  getCurrentSession(): string {
    const hour = new Date().getUTCHours();
    if (hour >= 8 && hour < 16) return 'LONDON';
    if (hour >= 13 && hour < 21) return 'NEW YORK';
    if (hour >= 23 || hour < 8) return 'ASIA';
    return 'TRANSITION';
  }

  getNextEvent(): string {
    if (this.analysis.fundamentals?.has_high_impact_events) {
      return this.analysis.fundamentals.events[0] || 'High Impact Event';
    }
    return 'Clean Calendar';
  }

  getPullbackReasons(): string[] {
    return this.analysis.pullback_warning?.reasons || [];
  }

  getScalingStrategy(): { stage: string, percent: number, target: string }[] {
    const vr = this.analysis.volatility_risk;
    if (!vr) return [];

    // Fallback logic for targets
    const tp1 = vr.take_profit_level1 ? `\$${vr.take_profit_level1.toFixed(2)}` : 'ATR 1.0x';
    const tp2 = vr.take_profit_level2 ? `\$${vr.take_profit_level2.toFixed(2)}` : 'ATR 2.0x';
    const tp3 = vr.take_profit ? `\$${vr.take_profit.toFixed(2)}` : 'Runner';

    return [
      { stage: 'Tactical De-risk', percent: 50, target: tp1 },
      { stage: 'Core Profit', percent: 30, target: tp2 },
      { stage: 'Infinite Runner', percent: 20, target: tp3 }
    ];
  }

  getMarketRegime(): string {
    const phase = this.analysis.market_phase.phase.toUpperCase();
    const trend = this.analysis.monthly_trend.direction.toUpperCase();
    return `${trend} | ${phase}`;
  }

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
  showMoreIntel = false;

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

  // ── Trade Execution Level Helpers ─────────────────────────────────────────
  private get isBullish(): boolean {
    return this.analysis.trade_signal.recommendation !== 'bearish';
  }

  getPricePositionPercent(): number {
    const pp = this.analysis.technical_indicators?.pivot_points;
    if (!pp) return 50;
    const price = this.analysis.current_price;
    const range = pp.r2 - pp.s2;
    if (range === 0) return 50;
    const percent = ((price - pp.s2) / range) * 100;
    return Math.max(0, Math.min(100, percent));
  }


  getVWAPClass(): string {
    const dist = this.analysis.daily_strength.vwap_dist_pct;
    if (dist === undefined || dist === null) return 'neutral';
    if (dist > 1.5) return 'bearish';
    if (dist < -1.5) return 'bullish';
    return 'neutral';
  }

  getSigmaPosition(sigma: number): number {
    const pp = this.analysis.technical_indicators?.pivot_points;
    const s1 = this.analysis.technical_indicators?.std_dev_1 || 0;
    if (!pp || s1 === 0) return 50;

    const range = (pp.r2 - pp.s2);
    if (range === 0) return 50;

    // Position of Pivot + (sigma * std_dev_1) relative to S2-R2 range
    const val = pp.pivot + (sigma * s1);
    const percent = ((val - pp.s2) / range) * 100;
    return Math.max(0, Math.min(100, percent));
  }

  getRSIDivergenceLabel(): string {
    const div = this.analysis.technical_indicators?.rsi_divergence;
    if (div === 'bullish') return '🐂 Bullish Divergence';
    if (div === 'bearish') return '🐻 Bearish Divergence';
    return '';
  }

  getEntryZone(): string {
    const entry = this.analysis.position_sizing?.entry_price ?? this.analysis.current_price;
    const s1 = this.analysis.technical_indicators?.pivot_points?.s1;
    const ret382 = this.analysis.technical_indicators?.fibonacci?.ret_382;
    if (this.isBullish && s1 && ret382) {
      const low = Math.min(s1, ret382);
      const high = Math.max(s1, ret382);
      return `${low.toFixed(2)} – ${high.toFixed(2)}`;
    }
    return entry.toFixed(2);
  }

  getEntryType(): string {
    const pp = this.analysis.technical_indicators?.pivot_points;
    const price = this.analysis.current_price;
    if (!pp) return 'Limit order';
    const s1 = pp.s1;
    if (this.isBullish) {
      return price > s1 ? 'Wait — above entry zone' : 'Limit at pullback';
    }
    return price < pp.r1 ? 'Wait — below entry zone' : 'Limit at pullback';
  }

  getBreakEvenLevel(): string {
    const entry = this.analysis.position_sizing?.entry_price ?? this.analysis.current_price;
    const atr = this.analysis.volatility_risk.atr;
    const be = this.isBullish ? entry + atr : entry - atr;
    return be.toFixed(2);
  }

  getTP1Fallback(): number {
    const entry = this.analysis.position_sizing?.entry_price ?? this.analysis.current_price;
    const atr = this.analysis.volatility_risk.atr;
    return this.isBullish ? entry + atr * 1.5 : entry - atr * 1.5;
  }

  getTP2Fallback(): number {
    const entry = this.analysis.position_sizing?.entry_price ?? this.analysis.current_price;
    const atr = this.analysis.volatility_risk.atr;
    return this.isBullish ? entry + atr * 2.5 : entry - atr * 2.5;
  }

  getInvalidationLevel(): string {
    const pp = this.analysis.technical_indicators?.pivot_points;
    const sl = this.analysis.volatility_risk.stop_loss;
    if (pp) {
      // Invalidation = beyond S2 for longs, beyond R2 for shorts
      const level = this.isBullish ? Math.min(pp.s2, sl) : Math.max(pp.r2, sl);
      return level.toFixed(2);
    }
    return sl.toFixed(2);
  }

  getInvalidationReason(): string {
    const pp = this.analysis.technical_indicators?.pivot_points;
    if (pp) {
      return this.isBullish
        ? 'Close below S2 invalidates bullish structure'
        : 'Close above R2 invalidates bearish structure';
    }
    return 'Trade thesis failed — exit immediately';
  }

  // ── Pre-Trade Checklist ───────────────────────────────────────────────────
  getTrendCheck(): 'pass' | 'warn' | 'fail' {
    const dir = this.analysis.monthly_trend.direction;
    const rec = this.analysis.trade_signal.recommendation;
    if (dir === rec) return 'pass';
    if (dir === 'neutral' || rec === 'neutral') return 'warn';
    return 'fail'; // trend conflicts with signal
  }

  getMomentumCheck(): 'pass' | 'warn' | 'fail' {
    const adx = this.analysis.daily_strength.adx;
    if (adx >= 25) return 'pass';
    if (adx >= 15) return 'warn';
    return 'fail';
  }

  getVolumeCheck(): 'pass' | 'warn' | 'fail' {
    const vol = this.analysis.daily_strength.volume_ratio;
    if (vol >= 1.0) return 'pass';
    if (vol >= 0.5) return 'warn';
    return 'fail';
  }

  getRSICheck(): 'pass' | 'warn' | 'fail' {
    const rsi = this.analysis.daily_strength.rsi;
    const isBull = this.isBullish;
    if (isBull) {
      if (rsi > 75) return 'fail'; // overbought
      if (rsi > 65) return 'warn';
      return 'pass';
    } else {
      if (rsi < 25) return 'fail'; // oversold
      if (rsi < 35) return 'warn';
      return 'pass';
    }
  }

  getBetaCheck(): 'pass' | 'warn' | 'fail' {
    const beta = this.analysis.benchmark_direction;
    const rec = this.analysis.trade_signal.recommendation;
    if (beta === rec) return 'pass';
    if (beta === 'neutral') return 'warn';
    return 'fail';
  }

  getPullbackCheck(): 'pass' | 'warn' | 'fail' {
    const score = this.analysis.pullback_warning?.warning_score ?? 0;
    if (score <= 2) return 'pass';
    if (score <= 4) return 'warn';
    return 'fail';
  }

  getOverallCheckClass(): string {
    const checks = [
      this.getTrendCheck(), this.getMomentumCheck(), this.getVolumeCheck(),
      this.getRSICheck(), this.getBetaCheck(), this.getPullbackCheck()
    ];
    const fails = checks.filter(c => c === 'fail').length;
    const warns = checks.filter(c => c === 'warn').length;
    if (fails >= 2) return 'no-go';
    if (fails >= 1 || warns >= 3) return 'caution';
    return 'go';
  }

  getTradeVerdict(): string {
    const cls = this.getOverallCheckClass();
    const score = this.analysis.trade_signal.score;
    if (cls === 'go') return `🟢 GO — All conditions met. Score ${score}. Execute at entry zone.`;
    if (cls === 'caution') return `⚠️ CAUTION — Mixed signals. Reduce size 50%. Score ${score}.`;
    return `🔴 NO-GO — Conditions not met. Wait for alignment. Score ${score}.`;
  }


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

