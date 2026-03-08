import { Component, Input, Output, EventEmitter, inject, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis, MarketAnalyzerService, ChartData, NewsItem } from '../../services/market-analyzer.service';
import { InstrumentChartComponent } from '../instrument-chart/instrument-chart.component';
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
                  {{ analysis.daily_strength.price_change_percent > 0 ? '+' : '' }}{{ analysis.daily_strength.price_change_percent.toFixed(2) }}% · 1D
                </span>
              </div>
            </div>
            <div class="th-badges">
              <span class="th-badge strategy" [class]="analysis.strategy_mode">
                {{ analysis.strategy_mode === 'long_term' ? '📈' : '⚡' }}
              </span>
              <div class="th-clocks">
                <span class="th-clock session" [class]="getCurrentSession().toLowerCase().replace(' ', '-')">{{ getCurrentSession() }}</span>
                <span class="th-clock event" [class.impact]="analysis.fundamentals.has_high_impact_events">{{ getNextEvent() }}</span>
              </div>
            </div>
          </div>

          <div class="th-right-compact">
            <div class="th-status-pill" [class]="getSignalClass()">
               <span class="th-s-val">{{ analysis.trade_signal.score }}</span>
               <span class="th-s-rec">{{ analysis.trade_signal.recommendation }}</span>
               @if (analysis.trade_signal.signal_conflict?.conflict_type && analysis.trade_signal.signal_conflict?.conflict_type !== 'none') {
                 <span class="th-conflict-badge" [class]="'sev-' + analysis.trade_signal.signal_conflict!.severity">⚡ CONFLICT</span>
               }
            </div>
            <button class="btn-refresh-circle" (click)="onRefresh()">🔄</button>
          </div>
        </header>

        <!-- 2.5 SIGNAL REASONS STRIP (compact) -->
        <div class="signal-reasons-strip">
          @for (reason of analysis.trade_signal.reasons; track reason) {
            <span class="syn-tag" [class]="getReasonImpactClass(reason)">{{ reason }}</span>
          }
        </div>

        <!-- EXPERT BATTLE PLAN (always visible, above tabs) -->
        @if (analysis.expert_trade_plan) {
        <div class="expert-above-tabs" [class.high-intent]="analysis.expert_trade_plan.is_high_intent">
          <div class="eat-header-row">
            <span class="eat-title">🎖️ EXPERT BATTLE PLAN</span>
            <span class="eat-rvol" [class.rvol-hot]="analysis.expert_trade_plan.rvol >= 1.8">
              RVOL {{ analysis.expert_trade_plan.rvol }}x
              @if (analysis.expert_trade_plan.is_high_intent) { 🔥 }
            </span>
            <span class="plan-age" [class.plan-age--stale]="isPlanStale()">🕐 {{ getAnalysisAge() }}</span>
          </div>
          <p class="eat-text">{{ analysis.expert_trade_plan.battle_plan }}</p>
        </div>
        }

        <!-- ANALYSIS TABS NAVIGATION -->
        <div class="analysis-tabs">
          <button class="atab" [class.active]="activeAnalysisTab === 'technical'" (click)="activeAnalysisTab = 'technical'">SIGNAL</button>
          <button class="atab" [class.active]="activeAnalysisTab === 'risk'" (click)="activeAnalysisTab = 'risk'">RISK</button>
          <button class="atab" [class.active]="activeAnalysisTab === 'performance'" (click)="activeAnalysisTab = 'performance'">PERFORMANCE</button>
        </div>

          @if (activeAnalysisTab === 'technical') {
          <section class="t-tile intel-tile tab-content-tile">
            <div class="intel-column-stack">

              <!-- CONFLICT DETAIL (inline, compact) -->
              @if (analysis.trade_signal.signal_conflict?.conflict_type && analysis.trade_signal.signal_conflict?.conflict_type !== 'none') {
              <div class="conflict-inline" [class]="'ci-' + analysis.trade_signal.signal_conflict!.severity">
                <span class="ci-text">{{ analysis.trade_signal.signal_conflict!.guidance }}</span>
                @if (analysis.trade_signal.signal_conflict!.trigger_price_up) {
                  <span class="ci-trigger bullish">▲ \${{ analysis.trade_signal.signal_conflict!.trigger_price_up?.toFixed(2) }}</span>
                }
                @if (analysis.trade_signal.signal_conflict!.trigger_price_down) {
                  <span class="ci-trigger bearish">▼ \${{ analysis.trade_signal.signal_conflict!.trigger_price_down?.toFixed(2) }}</span>
                }
              </div>
              }

              <!-- SECTION 1: STRATEGIC ACTION & SCALING -->
              <div class="tech-section action-section">
                <div class="tile-header">
                  🎯 STRATEGIC ACTION & SCALING
                  <span class="action-rec-badge" [class]="isWaitAction() ? 'badge-wait' : getSignalClass()">{{ analysis.trade_signal.action_plan }}</span>
                </div>
                <div class="action-hero">
                   <div class="aph-sub">{{ analysis.trade_signal.action_plan_details }}</div>
                </div>

                <div class="levels-stack" [class.levels-inactive]="isWaitAction()">
                  @if (isWaitAction()) {
                    <div class="levels-pending">⏸ Levels pending signal confirmation — wait for alignment before entering</div>
                  }
                  <div class="lvl-box entry"><span class="ll">ENTRY</span><span class="lv">\${{ getEntryZone() }}</span></div>
                  <div class="lvl-box sl"><span class="ll">STOP</span><span class="lv bearish">\${{ analysis.volatility_risk.stop_loss.toFixed(2) }}</span></div>
                  <div class="lvl-box tp"><span class="ll">TARGET</span><span class="lv bullish">\${{ analysis.volatility_risk.take_profit.toFixed(2) }}</span></div>
                </div>

                <div class="rr-visual-diagram">
                  <div class="rrd-header">VISUAL R/R DIAGRAM</div>
                  <div class="rrd-chart">
                    <div class="rrd-row">
                      <span class="rrd-tag tp-tag">TARGET</span>
                      <div class="rrd-bar tp-bar"></div>
                      <span class="rrd-price bullish">\${{ analysis.volatility_risk.take_profit.toFixed(2) }}</span>
                    </div>
                    <div class="rrd-row reward-row">
                      <span class="rrd-amount bullish">▲ +\${{ getRRReward() }} REWARD</span>
                    </div>
                    <div class="rrd-row">
                      <span class="rrd-tag entry-tag">ENTRY ●</span>
                      <div class="rrd-bar entry-bar"></div>
                      <span class="rrd-price">\${{ getEntryZone() }}</span>
                    </div>
                    <div class="rrd-row risk-row">
                      <span class="rrd-amount bearish">▼ -\${{ getRRRisk() }} RISK</span>
                    </div>
                    <div class="rrd-row">
                      <span class="rrd-tag sl-tag">STOP</span>
                      <div class="rrd-bar sl-bar"></div>
                      <span class="rrd-price bearish">\${{ analysis.volatility_risk.stop_loss.toFixed(2) }}</span>
                    </div>
                  </div>
                  <div class="rrd-stats">
                    <div class="rrd-stat"><span>R/R RATIO</span><strong class="bullish">{{ getRRRatio() }}:1</strong></div>
                    <div class="rrd-stat"><span>EXP. VALUE</span><strong class="bullish">+\${{ getExpectedValue() }}</strong></div>
                    <div class="rrd-stat"><span>ACC. RISK</span><strong>{{ getRiskAmount() }}</strong></div>
                    <div class="rrd-stat"><span>SIGNAL SCORE</span><strong [class]="getSignalClass()">{{ analysis.trade_signal.score }}</strong></div>
                  </div>
                </div>

                <div class="terminal-gauge">
                   <div class="tg-track">
                      <div class="tg-fill" [style.left.%]="getPricePositionPercent()"></div>
                      <div class="tg-marker pivot" style="left: 50%"></div>
                   </div>
                   <div class="tg-labels"><span>S1</span><span>PIVOT</span><span>R1</span></div>
                </div>

                <div class="scaling-zone">
                    <div class="sz-header">⚖️ FIXED SCALING ENTRIES (50 / 30 / 20)</div>
                    <div class="sz-grid">
                        @for (step of getScalingStrategy(); track step.stage) {
                          <div class="sz-item" [class.sz-item--hit]="isTargetHit(step.target)" [class.sz-item--next]="isNextTarget(step.target)">
                             <div class="sz-top"><span>{{ step.percent }}% ALLOC</span><strong>{{ step.stage }}</strong></div>
                             <div class="sz-val">{{ step.target }}</div>
                             <div class="sz-dist">{{ getTargetDistance(step.target) }}</div>
                          </div>
                        }
                    </div>
                    <!-- Scaling Interpretation -->
                    <div class="sz-interpretation">
                      <p class="sz-action-read">{{ getScalingActionRead() }}</p>
                    </div>
                </div>

                <div class="mm-footer">
                   <div class="mmf-item"><span>LOTS</span><strong>{{ getCalculatedLotSize() }}</strong></div>
                   <div class="mmf-item"><span>ENTRY</span><strong>\${{ (analysis.position_sizing?.entry_price ?? analysis.current_price)?.toFixed(2) }}</strong></div>
                </div>

              </div>


              <!-- MARKET MOMENTUM READ -->
              <div class="tech-section momentum-read-section">
                <div class="tile-header">📊 MARKET MOMENTUM READ</div>
                <div class="mmr-grid">
                  <div class="mmr-item">
                    <span class="mmr-lbl">ADX</span>
                    <strong class="mmr-val">{{ analysis.daily_strength.adx.toFixed(0) }}</strong>
                    <span class="mmr-interp" [class]="getADXClass()">{{ getADXInterpretation() }}</span>
                  </div>
                  <div class="mmr-item">
                    <span class="mmr-lbl">RSI</span>
                    <strong class="mmr-val">{{ analysis.daily_strength.rsi.toFixed(0) }}</strong>
                    <span class="mmr-interp" [class]="getRSIClass()">{{ getRSIInterpretation() }}</span>
                  </div>
                  <div class="mmr-item">
                    <span class="mmr-lbl">IMPACT</span>
                    <strong class="mmr-val" [class]="getTechnicalHeatClass()">{{ getTechnicalHeatImpact() }}</strong>
                    <span class="mmr-interp">{{ getTechnicalRecommendation() }}</span>
                  </div>
                  <div class="mmr-item">
                    <span class="mmr-lbl">VWAP DIST</span>
                    <strong class="mmr-val" [class]="getVWAPClass()">{{ analysis.daily_strength.vwap_dist_pct != null ? (analysis.daily_strength.vwap_dist_pct.toFixed(2) + '%') : 'N/A' }}</strong>
                    <span class="mmr-interp" [class]="getVWAPClass()">{{ getVWAPDistLabel() }}</span>
                  </div>
                </div>
                <div class="mmr-combined-read">{{ getMarketMomentumRead() }}</div>

                <div class="mmr-plan">
                  <div class="mmr-plan-header">
                    <span>🧠 TACTICAL INTERPRETATION ({{ getTacticalContextLabel() }})</span>
                    <span class="mmr-bias" [class]="getTacticalBiasClass()">{{ getTacticalBiasText() }}</span>
                  </div>

                  <ul class="mmr-evidence">
                    @for (line of getTacticalEvidence(); track line) {
                      <li>{{ line }}</li>
                    }
                  </ul>

                  <div class="mmr-scenarios">
                    <div class="mmr-scenario bull">
                      <div class="sc-title">LONG CONTINUATION SCENARIO</div>
                      <div class="sc-row"><span>TRIGGER</span><strong>{{ getBullTriggerText() }}</strong></div>
                      <div class="sc-row"><span>TARGET</span><strong>{{ getBullTargetText() }}</strong></div>
                      <div class="sc-row"><span>INVALIDATION</span><strong>{{ getBullInvalidationText() }}</strong></div>
                    </div>
                    <div class="mmr-scenario bear">
                      <div class="sc-title">SHORT REVERSAL SCENARIO</div>
                      <div class="sc-row"><span>TRIGGER</span><strong>{{ getBearTriggerText() }}</strong></div>
                      <div class="sc-row"><span>TARGET</span><strong>{{ getBearTargetText() }}</strong></div>
                      <div class="sc-row"><span>INVALIDATION</span><strong>{{ getBearInvalidationText() }}</strong></div>
                    </div>
                  </div>

                  <div class="mmr-plan-note">{{ getTacticalExecutionNote() }}</div>
                </div>
              </div>

              <!-- SECTION 2: PIVOT MATRIX & EXTENSIONS -->
              <div class="tech-section pivot-section">
                <div class="tile-header">📐 PIVOT MATRIX & EXTENSIONS</div>
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
                <!-- Pivot Interpretation -->
                @if (analysis.technical_indicators?.pivot_points) {
                <div class="pivot-interpretation">
                  <div class="pi-bias-row">
                    <span class="pi-badge" [class]="getPivotBias()">{{ getPricePosition() }}</span>
                    <span class="pi-align-tag" [class]="getPivotSignalAlignClass()">{{ getPivotSignalAlign() }}</span>
                  </div>
                  <p class="pi-read-text">{{ getPivotTradeRead() }}</p>
                  <div class="pi-key-levels">
                    <div class="pi-kl res">
                      <span>NEXT RESISTANCE</span>
                      <strong>\${{ getNearestResistance() }}</strong>
                    </div>
                    <div class="pi-kl sup">
                      <span>NEAREST SUPPORT</span>
                      <strong>\${{ getNearestSupport() }}</strong>
                    </div>
                  </div>
                  @if (getFibZoneRead()) {
                    <div class="pi-fib-note">{{ getFibZoneRead() }}</div>
                  }
                </div>
                }
              </div>



              <!-- P6: VOLUME PROFILE -->
              @if (analysis.volume_profile) {
              <div class="intel-block">
                <div class="tile-header">📦 VOLUME PROFILE</div>
                <div class="vp-key-levels">
                  <div class="vp-lvl poc"><span>POC</span><strong>\${{ analysis.volume_profile.poc.toFixed(2) }}</strong></div>
                  <div class="vp-lvl vah"><span>VAH</span><strong class="bullish">\${{ analysis.volume_profile.vah.toFixed(2) }}</strong></div>
                  <div class="vp-lvl val"><span>VAL</span><strong class="bearish">\${{ analysis.volume_profile.val.toFixed(2) }}</strong></div>
                </div>
                <div class="vp-sparkline">
                  @for (bucket of getTopVPBuckets(); track bucket.price_low) {
                    <div class="vp-bar-row">
                      <div class="vp-price">\${{ bucket.price_low.toFixed(0) }}</div>
                      <div class="vp-bar-track">
                        <div class="vp-bar-fill" [class.poc-bar]="bucket.is_poc" [style.width.%]="bucket.pct_of_max"></div>
                      </div>
                    </div>
                  }
                </div>
                <p class="vp-interpretation">{{ analysis.volume_profile.interpretation }}</p>
              </div>
              }

              <!-- P7: SESSION VWAP -->
              @if (analysis.session_vwap && analysis.session_vwap.vwap > 0 && analysis.strategy_mode === 'short_term') {
              <div class="intel-block">
                <div class="tile-header">〰️ SESSION VWAP</div>
                <div class="vwap-grid">
                  <div class="vwap-cell"><span>VWAP</span><strong>\${{ analysis.session_vwap.vwap.toFixed(2) }}</strong></div>
                  <div class="vwap-cell"><span>UPPER</span><strong class="bullish">\${{ analysis.session_vwap.upper_band.toFixed(2) }}</strong></div>
                  <div class="vwap-cell"><span>LOWER</span><strong class="bearish">\${{ analysis.session_vwap.lower_band.toFixed(2) }}</strong></div>
                  <div class="vwap-cell"><span>DIST</span><strong [class]="analysis.session_vwap.distance_pct >= 0 ? 'bullish' : 'bearish'">{{ analysis.session_vwap.distance_pct >= 0 ? '+' : '' }}{{ analysis.session_vwap.distance_pct.toFixed(2) }}%</strong></div>
                </div>
                <div class="vwap-position-badge" [class]="getVWAPPositionClass()">
                  {{ analysis.session_vwap.position }}
                </div>
                <p class="vwap-interpretation">{{ analysis.session_vwap.interpretation }}</p>
              </div>
              }

            </div>
          </section>
          }

          @if (activeAnalysisTab === 'risk') {
          <section class="t-tile status-tile tab-content-tile">
            <div class="risk-dual-panel">
              <div class="risk-panel-card">
                <div class="tile-header">🛡️ VALIDATION & RISK INTEL</div>
                <div class="checklist-compact-full">
                  <div class="ch-item" [class]="getTrendCheck()">
                     <div class="ch-left-data"><span class="ch-i">Trend Structure</span><span class="ch-v">{{ analysis.monthly_trend.direction | uppercase }}</span></div>
                     <div class="ch-correlation">{{ getTrendCorrelation() }}</div>
                  </div>
                  <div class="ch-item" [class]="getMomentumCheck()">
                     <div class="ch-left-data"><span class="ch-i">Momentum (ADX)</span><span class="ch-v">{{ analysis.daily_strength.adx.toFixed(0) }}</span></div>
                     <div class="ch-correlation">{{ getMomentumCorrelation() }}</div>
                  </div>
                  <div class="ch-item" [class]="getVolatilityCheck()">
                     <div class="ch-left-data"><span class="ch-i">Volatility Risk</span><span class="ch-v">{{ getVolatilityLevel() }}</span></div>
                     <div class="ch-correlation">{{ getVolatilityCorrelation() }}</div>
                  </div>
                  <div class="ch-item" [class]="getVolumeCheck()">
                     <div class="ch-left-data"><span class="ch-i">Volume Analysis</span><span class="ch-v">{{ getVolumeStatus() }}</span></div>
                     @if (getVolumeStatus() !== 'ANALYZING') {
                       <div class="ch-correlation">{{ getVolumeCorrelation() }}</div>
                     } @else {
                       <div class="ch-correlation muted">Insufficient volume data — computing</div>
                     }
                  </div>
                  <div class="ch-item" [class]="getSupportResistanceCheck()">
                     <div class="ch-left-data"><span class="ch-i">Key Levels</span><span class="ch-v">{{ getLevelStatus() }}</span></div>
                     <div class="ch-correlation">{{ getLevelCorrelation() }}</div>
                  </div>
                  <div class="ch-item" [class]="getVolatilityRegimeCheck()">
                     <div class="ch-left-data"><span class="ch-i">Volatility Regime</span><span class="ch-v">{{ analysis.volatility_risk.volatility_regime_label }}</span></div>
                     <div class="ch-correlation">ATR {{ analysis.volatility_risk.atr_percentile_rank?.toFixed(0) }}th %ile · HV {{ analysis.volatility_risk.historical_volatility_14?.toFixed(1) }}%</div>
                  </div>
                </div>

                @if (analysis.instrument_correlations &&
                     !(analysis.instrument_correlations.interpretation?.toLowerCase()?.includes('insufficient')) &&
                     (analysis.instrument_correlations.vs_dxy != null || analysis.instrument_correlations.vs_spx != null || analysis.instrument_correlations.vs_btc != null)) {
                <div class="corr-matrix-row">
                  <div class="cm-label">30-DAY CORRELATIONS</div>
                  <div class="cm-cells">
                    @if (analysis.instrument_correlations.vs_dxy !== null && analysis.instrument_correlations.vs_dxy !== undefined) {
                      <div class="cm-cell" [class]="getCorrCellClass(analysis.instrument_correlations.vs_dxy)">
                        <span>vs DXY</span><strong>{{ analysis.instrument_correlations.vs_dxy > 0 ? '+' : '' }}{{ analysis.instrument_correlations.vs_dxy?.toFixed(2) }}</strong>
                      </div>
                    }
                    @if (analysis.instrument_correlations.vs_spx !== null && analysis.instrument_correlations.vs_spx !== undefined) {
                      <div class="cm-cell" [class]="getCorrCellClass(analysis.instrument_correlations.vs_spx)">
                        <span>vs SPX</span><strong>{{ analysis.instrument_correlations.vs_spx > 0 ? '+' : '' }}{{ analysis.instrument_correlations.vs_spx?.toFixed(2) }}</strong>
                      </div>
                    }
                    @if (analysis.instrument_correlations.vs_btc !== null && analysis.instrument_correlations.vs_btc !== undefined) {
                      <div class="cm-cell" [class]="getCorrCellClass(analysis.instrument_correlations.vs_btc)">
                        <span>vs BTC</span><strong>{{ analysis.instrument_correlations.vs_btc > 0 ? '+' : '' }}{{ analysis.instrument_correlations.vs_btc?.toFixed(2) }}</strong>
                      </div>
                    }
                  </div>
                  <div class="cm-interpretation">{{ analysis.instrument_correlations.interpretation }}</div>
                </div>
                }
              </div>

              <div class="risk-panel-card">
                <div class="tile-header">⚠️ PULLBACK & TRAP ANALYSIS</div>
                <p class="pic-desc">{{ analysis.pullback_warning?.description || 'No immediate pullback or trap risk detected. Current price action appears normal.' }}</p>
                <div class="pic-reasons">
                    @if (hasPullbackReasons()) {
                        @for (reason of analysis.pullback_warning!.reasons; track reason) {
                            <div class="pic-reason-tag" [class]="getPullbackReasonClass(reason)">◈ {{ reason }}</div>
                        }
                    } @else {
                        <div class="pic-reason-tag neutral">◈ Market conditions stable</div>
                        <div class="pic-reason-tag neutral">◈ No trap patterns identified</div>
                        <div class="pic-reason-tag neutral">◈ Normal price progression</div>
                    }
                </div>
                <div class="pic-metrics">
                    <div class="pic-metric">
                        <span class="pic-metric-label">Risk Level</span>
                        <span class="pic-metric-value" [class]="getPullbackRiskClass()">{{ getPullbackRiskLevel() }}</span>
                    </div>
                    <div class="pic-metric">
                        <span class="pic-metric-label">Current Position</span>
                        <span class="pic-metric-value">{{ getPullbackPosition() }}</span>
                    </div>
                    <div class="pic-metric">
                        <span class="pic-metric-label">Recommended Action</span>
                        <span class="pic-metric-value">{{ getPullbackAction() }}</span>
                    </div>
                </div>

              </div>
            </div>

            <!-- MACRO REGIME -->
            <div class="macro-context-block">
              <div class="tile-header">🌐 MACRO REGIME</div>
              <div class="macro-mini">
                <div class="mm-item"><span>Phase</span><strong [class]="getPhaseClass()">{{ analysis.market_phase.phase | uppercase }}</strong></div>
                <div class="mm-item"><span>Score</span><strong>{{ analysis.market_phase.score }}</strong></div>
              </div>
              <p class="intel-text-sm">{{ analysis.market_phase.description }}</p>
            </div>

            <!-- LIQUIDITY MAP -->
            @if (analysis.liquidity_map) {
            <div class="liquidity-map-section">
              <div class="tile-header">🗺️ LIQUIDITY MAP</div>
              <div class="lm-dual">
                <div class="lm-col">
                  <div class="lm-col-header bearish">RESISTANCE</div>
                  @for (lvl of analysis.liquidity_map.resistance_levels; track lvl.price) {
                    <div class="lm-level" [class]="'lm-' + lvl.strength">
                      <span class="lm-price bearish">\${{ lvl.price.toFixed(2) }}</span>
                      <span class="lm-dist">+{{ lvl.distance_pct.toFixed(1) }}%</span>
                      <span class="lm-badge" [class]="'strength-' + lvl.strength">{{ lvl.strength }}</span>
                    </div>
                  }
                </div>
                <div class="lm-col">
                  <div class="lm-col-header bullish">SUPPORT</div>
                  @for (lvl of analysis.liquidity_map.support_levels; track lvl.price) {
                    <div class="lm-level" [class]="'lm-' + lvl.strength">
                      <span class="lm-price bullish">\${{ lvl.price.toFixed(2) }}</span>
                      <span class="lm-dist">-{{ lvl.distance_pct.toFixed(1) }}%</span>
                      <span class="lm-badge" [class]="'strength-' + lvl.strength">{{ lvl.strength }}</span>
                    </div>
                  }
                </div>
              </div>
              <p class="lm-interpretation">{{ analysis.liquidity_map.interpretation }}</p>
            </div>
            }

            @if (analysis.fundamentals?.risk_reduction_active || analysis.fundamentals?.pre_event_caution) {
            <div class="pre-event-alert" [class]="analysis.fundamentals.risk_reduction_active ? 'pea-active' : 'pea-caution'">
              <div class="pea-header">
                <span>{{ analysis.fundamentals.risk_reduction_active ? '🔴' : '🟡' }}</span>
                <span class="pea-title">{{ analysis.fundamentals.risk_reduction_active ? 'RISK REDUCTION ACTIVE' : 'PRE-EVENT CAUTION' }}</span>
                @if (analysis.fundamentals.minutes_to_next_event) {
                  <span class="pea-countdown">{{ getEventCountdown(analysis.fundamentals.minutes_to_next_event) }}</span>
                }
              </div>
              <div class="pea-body">
                {{ analysis.fundamentals.risk_reduction_active
                   ? 'High-impact event within 60 min. Position size auto-capped at 50%.'
                   : 'High-impact event within 24h. Consider reducing size to 75%.' }}
              </div>
              @if (analysis.fundamentals.event_timestamps?.length) {
                <div class="pea-event">{{ analysis.fundamentals.event_timestamps[0].event }}</div>
              }
              <div class="pea-multiplier">
                Size Multiplier: <strong>×{{ analysis.fundamentals.recommended_position_multiplier?.toFixed(2) }}</strong>
              </div>
            </div>
            }

            <!-- P9: BLOCK FLOW DETECTOR (always in Risk tab) -->
            @if (analysis.block_flow) {
            <div class="block-flow-section" [class]="analysis.block_flow.detected ? 'bf-active' : 'bf-quiet'">
              <div class="tile-header">🐋 BLOCK FLOW DETECTOR</div>
              @if (!analysis.block_flow.detected) {
                <p class="bf-quiet-msg">{{ analysis.block_flow.interpretation }}</p>
              }
              @if (analysis.block_flow.detected) {
                <div class="bf-summary">
                  <div class="bf-direction" [class]="'bf-dir-' + analysis.block_flow.net_direction">
                    {{ analysis.block_flow.net_direction | uppercase }} FLOW
                  </div>
                  <div class="bf-counts">
                    <span class="bullish">{{ analysis.block_flow.bull_blocks }}🟢 Bull</span>
                    <span class="bearish">{{ analysis.block_flow.bear_blocks }}🔴 Bear</span>
                  </div>
                </div>
                <div class="bf-events">
                  @for (ev of analysis.block_flow.events.slice().reverse().slice(0, 3); track ev.timestamp) {
                    <div class="bf-event" [class]="'bf-' + ev.direction">
                      <span class="bf-ts">{{ ev.timestamp }}</span>
                      <span class="bf-p" [class]="ev.direction">\${{ ev.price.toFixed(2) }}</span>
                      <span class="bf-vol">{{ ev.volume_ratio }}x vol</span>
                    </div>
                  }
                </div>
                <p class="bf-interpretation">{{ analysis.block_flow.interpretation }}</p>
              }
            </div>
            }

            <!-- P10: GEOPOLITICAL RISK INTELLIGENCE -->
            @if (analysis.geopolitical_risk?.detected) {
            <div class="geo-risk-section" [class]="'geo-' + analysis.geopolitical_risk!.risk_level.toLowerCase()">
              <div class="geo-risk-header">
                <div class="geo-risk-title">
                  <span class="geo-risk-icon">🌍</span>
                  <span>GEOPOLITICAL RISK INTELLIGENCE</span>
                </div>
                <div class="geo-risk-score-badge" [class]="'geo-score-' + analysis.geopolitical_risk!.risk_level.toLowerCase()">
                  <span class="geo-score-val">{{ analysis.geopolitical_risk!.risk_score }}</span>
                  <span class="geo-score-label">/100</span>
                  <span class="geo-risk-level">{{ analysis.geopolitical_risk!.risk_level }}</span>
                </div>
              </div>

              <div class="geo-keywords">
                @for (kw of analysis.geopolitical_risk!.keywords_found; track kw) {
                  <span class="geo-kw-tag">{{ kw }}</span>
                }
              </div>

              <div class="geo-impact-row">
                <div class="geo-impact-cell">
                  <span class="geo-cell-label">EXPECTED IMPACT</span>
                  <span class="geo-cell-val" [class]="getGeoImpactClass(analysis.geopolitical_risk!.expected_impact)">
                    {{ analysis.geopolitical_risk!.expected_impact | uppercase }}
                  </span>
                </div>
                <div class="geo-impact-cell">
                  <span class="geo-cell-label">CONFIDENCE</span>
                  <span class="geo-cell-val">{{ analysis.geopolitical_risk!.impact_confidence }}</span>
                </div>
                <div class="geo-impact-cell">
                  <span class="geo-cell-label">PRICE ACTION</span>
                  <span class="geo-cell-val" [class]="getGeoConfirmationClass(analysis.geopolitical_risk!.indicator_confirmation)">
                    {{ analysis.geopolitical_risk!.indicator_confirmation }}
                  </span>
                </div>
              </div>

              <div class="geo-indicators">
                @for (ind of analysis.geopolitical_risk!.indicators; track ind.name) {
                  <div class="geo-ind-row" [class]="'geo-ind-' + ind.status">
                    <span class="geo-ind-icon">{{ ind.status === 'confirming' ? '✅' : ind.status === 'diverging' ? '❌' : '⚠️' }}</span>
                    <div class="geo-ind-content">
                      <span class="geo-ind-name">{{ ind.name }}</span>
                      <span class="geo-ind-desc">{{ ind.description }}</span>
                    </div>
                  </div>
                }
              </div>

              <div class="geo-narrative">{{ analysis.geopolitical_risk!.ai_narrative }}</div>

              <div class="geo-action-bias" [class]="getGeoActionClass(analysis.geopolitical_risk!.action_bias)">
                <span class="geo-action-label">ACTION BIAS</span>
                <span class="geo-action-val">{{ analysis.geopolitical_risk!.action_bias }}</span>
              </div>
            </div>
            }

          </section>
          }

          @if (activeAnalysisTab === 'performance') {
          <section class="t-tile perf-tab-tile tab-content-tile">
            <div class="perf-content">
              <div class="probability-box-v2">
                <div class="pb2-header">📈 PROBABILITY & BACKTEST QUALITY</div>
                <div class="pb2-grid">
                  <div class="pb2-stat"><span>WIN RATE</span><strong>{{ analysis.backtest_results.win_rate.toFixed(1) }}%</strong></div>
                  <div class="pb2-stat"><span>PROFIT FACTOR</span><strong>{{ analysis.backtest_results.profit_factor }}</strong></div>
                  <div class="pb2-stat"><span>SHARPE</span><strong [class]="analysis.backtest_results.sharpe_ratio >= 1 ? 'bullish' : 'bearish'">{{ analysis.backtest_results.sharpe_ratio?.toFixed(2) }}</strong></div>
                  <div class="pb2-stat"><span>EXPECTANCY</span><strong [class]="analysis.backtest_results.expectancy >= 0 ? 'bullish' : 'bearish'">{{ analysis.backtest_results.expectancy >= 0 ? '+' : '' }}{{ analysis.backtest_results.expectancy?.toFixed(2) }}%</strong></div>
                </div>
                <div class="pb2-grid pb2-grid-secondary">
                  <div class="pb2-stat"><span>MAX DD</span><strong class="bearish">{{ analysis.backtest_results.max_drawdown_pct?.toFixed(1) }}%</strong></div>
                  <div class="pb2-stat"><span>MAX STREAK</span><strong>{{ analysis.backtest_results.max_consecutive_losses }}L</strong></div>
                  <div class="pb2-stat"><span>SAMPLE</span><strong>n={{ analysis.backtest_results.sample_size }}</strong></div>
                  <div class="pb2-stat"><span>MAE</span><strong>{{ analysis.backtest_results.max_adverse_excursion_pct?.toFixed(1) }}% vs</strong></div>
                </div>
                @if (analysis.backtest_results.sample_size < 30) {
                  <div class="sample-size-warning">⚠ Low sample size (n={{ analysis.backtest_results.sample_size }}). Results are indicative only — not statistically significant until n≥30.</div>
                }
                <div class="bt-spark-v2">
                  <svg viewBox="0 0 200 60" preserveAspectRatio="none">
                    <polyline [attr.points]="getEquityCurvePoints()" class="spark-line" />
                  </svg>
                </div>
              </div>

              <!-- Chart Area in Performance tab -->
              <div class="perf-chart-area">
                <div class="tile-header">📉 PRICE CHART</div>
                <div class="terminal-chart-area">
                  <app-instrument-chart [data]="chartData" [symbol]="analysis.symbol" [overlayLevels]="getChartOverlays()" *ngIf="chartData.length > 0"></app-instrument-chart>
                  @if (!chartData.length) {
                    <div class="chart-placeholder">Chart data loading — click Refresh 🔄</div>
                  }
                </div>
              </div>
            </div>
          </section>
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
  `,
  styles: [`
    :host { display: block; width: 100%; margin-bottom: 30px; }
    .instrument-terminal { background: #0b0b15; border-radius: 16px; border: 1px solid #1a1a2a; overflow: hidden; }
    
    .terminal-banner { width: 100%; }
    
    .terminal-body { padding: 0; }
    .terminal-body.bullish { border-left: 3px solid #a6e3a1; }
    .terminal-body.bearish { border-left: 3px solid #f38ba8; }

    /* SIGNAL REASONS STRIP (replaces verbose AI Summary) */
    .signal-reasons-strip { display: flex; flex-direction: row; flex-wrap: wrap; align-items: flex-start; gap: 6px 8px; padding: 10px 16px; border-bottom: 1px solid #1f1f3a; background: rgba(17,17,27,0.4); }
    .syn-tag { font-size: 0.6rem; padding: 3px 9px; border-radius: 4px; background: #1a1a2a; border: 1px solid #313244; color: #9399b2; font-weight: 700; }
    .syn-tag.positive { background: rgba(166,227,161,0.1); color: #a6e3a1; border-color: rgba(166,227,161,0.3); }
    .syn-tag.negative { background: rgba(243,139,168,0.1); color: #f38ba8; border-color: rgba(243,139,168,0.3); }
    .syn-tag.neutral { background: rgba(249,226,175,0.1); color: #f9e2af; border-color: rgba(249,226,175,0.3); }
    .syn-tag.warning { background: rgba(250,179,135,0.1); color: #fab387; border-color: rgba(250,179,135,0.3); }
    .syn-tag.info { background: rgba(137,180,250,0.1); color: #89b4fa; border-color: rgba(137,180,250,0.3); }

    /* EXPERT BATTLE PLAN — above tabs (always visible) */
    .expert-above-tabs { padding: 14px 20px 16px; background: rgba(245,158,11,0.08); border-top: 1px solid rgba(245,158,11,0.35); border-bottom: 1px solid rgba(245,158,11,0.2); border-left: 4px solid #f59e0b; box-shadow: inset 4px 0 14px rgba(245,158,11,0.06); }
    .expert-above-tabs.high-intent { background: rgba(250,179,135,0.12); border-left-color: #fab387; border-top-color: rgba(250,179,135,0.45); box-shadow: inset 4px 0 18px rgba(250,179,135,0.1); animation: ebp-pulse 3s ease-in-out infinite; }
    @keyframes ebp-pulse { 0%, 100% { box-shadow: inset 4px 0 18px rgba(250,179,135,0.1); } 50% { box-shadow: inset 4px 0 28px rgba(250,179,135,0.2), 0 0 16px rgba(250,179,135,0.08); } }
    .eat-header-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .eat-title { font-size: 0.6rem; font-weight: 950; letter-spacing: 1.5px; color: #f59e0b; text-transform: uppercase; flex: 1; }
    .eat-rvol { font-size: 0.58rem; font-weight: 900; color: #6c7086; letter-spacing: 0.5px; }
    .eat-rvol.rvol-hot { color: #fab387; }
    .eat-text { font-size: 0.82rem; color: #e2e8f0; line-height: 1.7; margin: 0; font-weight: 500; white-space: pre-line; }

    /* HUD UPGRADE (ZERO WASTE) */
    .terminal-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 12px 16px; background: #0b0b15; border-bottom: 1px solid #1f1f3a; }
    .th-left { min-width: 0; flex: 1; }
    .th-right-compact { flex-shrink: 0; display: flex; align-items: center; gap: 12px; }
    .th-symbol-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap; }
    .th-symbol { font-size: 1.4rem; font-weight: 950; color: #cdd6f4; }
    .th-price-stack { display: flex; gap: 6px; align-items: baseline; min-width: 0; flex-wrap: wrap; }
    .th-price { font-size: 1.1rem; font-weight: 900; color: #bac2de; }
    .th-change { font-size: 0.8rem; font-weight: 800; }
    .th-badges { display: flex; gap: 6px; align-items: center; }
    .th-clock { font-size: 0.5rem; padding: 1px 4px; }
    .th-status-pill { padding: 4px 10px; border-radius: 4px; display: flex; align-items: center; gap: 8px; border: 1px solid; }
    .th-status-pill.bullish { border-color: #a6e3a1; color: #a6e3a1; background: rgba(166, 227, 161, 0.1); }
    .th-status-pill.bearish { border-color: #f38ba8; color: #f38ba8; background: rgba(243, 139, 168, 0.1); }
    .btn-refresh-circle { background: #1a1a2a; border: 1px solid #313244; color: #6c7086; padding: 6px; border-radius: 50%; cursor: pointer; }

    /* 3-COLUMN COMMAND CENTER (BALANCED UX) */
    .terminal-grid { display: grid; grid-template-columns: 1.1fr 1fr 1fr; gap: 0; background: #0b0b15; align-items: stretch; border-bottom: 2px solid #1f1f3a; }
    .t-tile { padding: 30px; border-right: 1px solid #1f1f3a; }
    .t-tile:last-child { border-right: none; }
    .tile-header { font-size: 0.65rem; font-weight: 950; color: #4b4d61; margin-bottom: 24px; text-transform: uppercase; letter-spacing: 1.5px; display: flex; align-items: center; gap: 8px; }

    /* Action Column CSS */
    .scaling-zone { margin: 24px 0; background: #11111b; border: 1px dashed #313244; padding: 16px; border-radius: 8px; }
    .sz-header { font-size: 0.55rem; color: #45475a; font-weight: 950; margin-bottom: 16px; }
    .sz-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .sz-item { background: #0b0b15; padding: 10px; border-radius: 6px; border: 1px solid #1f1f3a; text-align: center; transition: all 0.2s; }
    .sz-top { font-size: 0.45rem; color: #585b70; display: block; margin-bottom: 4px; }
    .sz-val { font-size: 0.85rem; font-weight: 950; color: #a6e3a1; }
    .sz-dist { font-size: 0.48rem; font-weight: 700; color: #45475a; margin-top: 4px; letter-spacing: 0.3px; }
    .sz-item--next { border-color: #89b4fa !important; background: rgba(137,180,250,0.06) !important; }
    .sz-item--next .sz-val { color: #89b4fa; }
    .sz-item--next .sz-dist { color: #89b4fa; }
    .sz-item--hit { border-color: rgba(166,227,161,0.4) !important; background: rgba(166,227,161,0.06) !important; opacity: 0.7; }
    .sz-item--hit .sz-val { color: #6c7086; text-decoration: line-through; }
    .sz-interpretation { margin-top: 14px; padding-top: 12px; border-top: 1px solid #1f1f3a; }
    .sz-action-read { font-size: 0.82rem; color: #cdd6f4; line-height: 1.65; margin: 0; padding: 12px 14px; background: rgba(137,180,250,0.05); border-left: 3px solid #89b4fa; border-radius: 0 6px 6px 0; font-weight: 500; }
    .sz-action-read:first-letter { font-size: 1rem; }
    .mm-footer { display: flex; gap: 10px; margin-bottom: 24px; }
    .mmf-item { flex: 1; padding: 12px; background: #121220; border-radius: 6px; text-align: center; }
    .mmf-item span { font-size: 0.5rem; color: #45475a; display: block; margin-bottom: 4px; }
    .mmf-item strong { font-size: 0.9rem; color: #cdd6f4; }

    /* Validation Column CSS */
    .pullback-intel-card { padding: 20px; background: #1e1e2e; border-radius: 12px; margin: 20px 0; border: 1px solid #313244; border-left: 5px solid #a6e3a1; }
    .pullback-intel-card.warn { border-left-color: #fab387; background: rgba(250, 179, 135, 0.05); }
    .pullback-intel-card.fail { border-left-color: #f38ba8; background: rgba(243, 139, 168, 0.05); }
    .pic-header { font-size: 0.6rem; font-weight: 950; color: #89b4fa; margin-bottom: 12px; }
    .pic-desc { font-size: 0.85rem; color: #cdd6f4; line-height: 1.4; margin-bottom: 16px; }
    .pic-reasons { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
    .pic-reason-tag { font-size: 0.65rem; padding: 4px 10px; background: #11111b; border-radius: 4px; color: #f38ba8; border: 1px solid rgba(243, 139, 168, 0.2); }
    .pic-reason-tag.high-risk { background: rgba(243, 139, 168, 0.1); color: #f38ba8; border-color: rgba(243, 139, 168, 0.3); }
    .pic-reason-tag.medium-risk { background: rgba(250, 179, 135, 0.1); color: #fab387; border-color: rgba(250, 179, 135, 0.3); }
    .pic-reason-tag.low-risk { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; border-color: rgba(166, 227, 161, 0.3); }
    .pic-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 16px; padding-top: 16px; border-top: 1px solid #313244; }
    .pic-metric { display: flex; flex-direction: column; gap: 4px; }
    .pic-metric-label { font-size: 0.5rem; color: #585b70; font-weight: 900; text-transform: uppercase; }
    .pic-metric-value { font-size: 0.8rem; font-weight: 950; color: #cdd6f4; }
    .pic-metric-value.high { color: #f38ba8; }
    .pic-metric-value.moderate { color: #fab387; }
    .pic-metric-value.low { color: #a6e3a1; }
    .probability-box-v2 { padding: 20px; background: #11111b; border-radius: 8px; margin-bottom: 24px; border: 1px solid #1f1f3a; }
    .pb2-header { font-size: 0.55rem; color: #45475a; font-weight: 950; margin-bottom: 12px; }
    .pb2-grid { display: flex; gap: 20px; margin-bottom: 12px; }
    .pb2-stat span { font-size: 0.5rem; color: #585b70; display: block; }
    .pb2-stat strong { font-size: 1.1rem; font-weight: 950; color: #cdd6f4; }
    .verdict-banner-final { padding: 18px; border-radius: 8px; text-align: center; font-size: 0.95rem; font-weight: 950; border: 1px solid transparent; }
    .verdict-banner-final.go { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; border-color: #a6e3a1; }
    .verdict-banner-final.caution { background: rgba(249, 226, 175, 0.1); color: #f9e2af; border-color: #f9e2af; }
    .verdict-banner-final.no-go { background: rgba(243, 139, 168, 0.1); color: #f38ba8; border-color: #f38ba8; }

    /* Intel Stack Column CSS */
    .intel-column-stack { display: flex; flex-direction: column; gap: 30px; }
    .intel-block { background: #11111b; padding: 20px; border-radius: 10px; border: 1px solid #1f1f3a; }
    .expert-intel-block { background: linear-gradient(135deg, rgba(137, 180, 250, 0.05), #11111b); border: 1px solid #313244; padding: 22px; border-radius: 10px; }
    .expert-intel-block.high-intent { border-color: #f38ba8; background: linear-gradient(135deg, rgba(243, 139, 168, 0.05), #11111b); }
    .macro-mini { display: flex; gap: 15px; margin-bottom: 12px; }
    .mm-item { flex: 1; padding: 10px; background: #0b0b15; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }
    .mm-item span { font-size: 0.5rem; color: #45475a; }
    .mm-item strong { font-size: 0.85rem; }
    .intel-text-sm { font-size: 0.8rem; color: #9399b2; line-height: 1.4; }
    .heat-bars { display: flex; flex-direction: column; gap: 12px; }
    .hb-item { display: flex; flex-direction: column; gap: 6px; }
    .hb-item span { font-size: 0.5rem; color: #585b70; text-transform: uppercase; }
    .hb-track { height: 4px; background: #0b0b15; border-radius: 2px; position: relative; }
    .hb-fill { height: 100%; border-radius: 2px; }
    .hb-fill.adx { background: #fab387; }
    .hb-fill.rsi { width: 8px; height: 8px; background: #cba6f7; border-radius: 50%; position: absolute; top: 50%; transform: translate(-50%, -50%); }
    .hb-interpretation { font-size: 0.6rem; color: #9399b2; margin-top: 4px; font-weight: 600; }
    .heat-context { margin-bottom: 12px; }
    .heat-intro { font-size: 0.75rem; color: #89b4fa; margin: 0; font-weight: 600; }
    .heat-implications { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #313244; }
    .heat-impact, .heat-recommendation { display: flex; justify-content: space-between; align-items: center; }
    .heat-label { font-size: 0.5rem; color: #585b70; font-weight: 900; text-transform: uppercase; }
    .heat-value { font-size: 0.7rem; font-weight: 950; }
    .heat-value.high { color: #f38ba8; }
    .heat-value.medium { color: #fab387; }
    .heat-value.low { color: #a6e3a1; }
    .events-mini-list { display: flex; flex-direction: column; gap: 6px; }
    .em-list-item { padding: 8px 12px; background: #0b0b15; border-radius: 4px; display: flex; justify-content: space-between; font-size: 0.75rem; color: #cdd6f4; }
    .em-list-item.high { border-left: 3px solid #f38ba8; }

    /* Footer CSS */
    .geopolitical-footer { padding: 40px; background: #0b0b15; }
    .geo-grid { display: grid; grid-template-columns: 350px 1fr; gap: 40px; align-items: start; }
    .sah-badge-v2 { padding: 12px 24px; font-size: 1.2rem; font-weight: 950; border-radius: 8px; text-align: center; margin-bottom: 16px; }
    .geo-headlines { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .news-pill-v2 { padding: 14px; background: #11111b; border: 1px solid #1f1f3a; border-radius: 8px; display: flex; flex-direction: column; gap: 6px; cursor: pointer; transition: all 0.2s; }
    .news-pill-v2:hover { border-color: #313244; background: #121220; }
    .np2-source { font-size: 0.5rem; color: #585b70; font-weight: 950; text-transform: uppercase; }
    .np2-title { font-size: 0.8rem; color: #cdd6f4; line-height: 1.3; font-weight: 600; }
    .np2-tag { font-size: 0.55rem; font-weight: 950; width: fit-content; padding: 2px 8px; border-radius: 4px; }
    .np2-tag.bullish { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }
    .np2-tag.bearish { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }

    /* EXPERT PANEL RESTORED */
    .expert-tile { background: linear-gradient(135deg, rgba(137, 180, 250, 0.03), transparent); }
    .expert-tile.high-intent { border-top: 3px solid #fab387; background: rgba(250, 179, 135, 0.05); }
    .expert-main { display: flex; flex-direction: column; gap: 16px; }
    .expert-header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
    .plan-age { font-size: 0.6rem; font-weight: 700; color: #585b70; letter-spacing: 0.3px; }
    .plan-age--stale { color: #f38ba8; }
    .expert-plan-text { font-size: 1.1rem; color: #cdd6f4; line-height: 1.4; font-weight: 500; margin-top: 0; }
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

    /* VALIDATION PANEL (CORRELATION UPGRADE) */
    .checklist-compact-full { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
    .ch-item { display: flex; flex-direction: column; gap: 6px; padding: 14px; background: #121220; border-radius: 8px; border: 1px solid #1f1f3a; transition: all 0.2s; }
    .ch-item:hover { border-color: #313244; background: #1a1a2a; }
    .ch-item.pass { border-left: 4px solid #a6e3a1; }
    .ch-item.warn { border-left: 4px solid #f9e2af; }
    .ch-item.fail { border-left: 4px solid #f38ba8; }
    
    .ch-left-data { display: flex; justify-content: space-between; align-items: center; }
    .ch-i { font-size: 0.6rem; font-weight: 800; color: #585b70; text-transform: uppercase; letter-spacing: 0.5px; }
    .ch-v { font-size: 0.9rem; font-weight: 950; color: #cdd6f4; }
    
    .ch-correlation { font-size: 0.75rem; color: #9399b2; line-height: 1.3; font-weight: 500; font-style: italic; }
    .ch-item.pass .ch-correlation { color: #a6e3a1; }
    .ch-item.fail .ch-correlation { color: #f38ba8; }
    .ch-item.warn .ch-correlation { color: #f9e2af; }

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

    /* ANALYSIS TABS */
    .analysis-tabs { display: flex; background: #0b0b15; border-bottom: 2px solid #1f1f3a; overflow-x: auto; flex-shrink: 0; }
    .analysis-tabs::-webkit-scrollbar { height: 0; }
    .atab { flex: 1; padding: 13px 8px; background: transparent; border: none; border-bottom: 3px solid transparent; color: #45475a; font-size: 0.6rem; font-weight: 800; cursor: pointer; text-transform: uppercase; letter-spacing: 0.5px; transition: all 0.2s; white-space: nowrap; min-width: 72px; }
    .atab:hover { color: #9399b2; background: rgba(137, 180, 250, 0.04); }
    .atab.active { color: #89b4fa; border-bottom-color: #89b4fa; background: rgba(137, 180, 250, 0.05); }
    .tab-content-tile { border-right: none; width: 100%; box-sizing: border-box; }
    .geo-tab-tile { padding: 30px; }
    .geo-deep-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #1f1f3a; }
    .expert-metrics { display: flex; gap: 8px; margin-top: 12px; }
    .em-pill { padding: 4px 10px; border-radius: 4px; background: #1a1a2a; border: 1px solid #313244; display: flex; gap: 6px; align-items: center; font-size: 0.7rem; color: #9399b2; }
    .em-pill span { font-size: 0.5rem; text-transform: uppercase; color: #45475a; }
    .em-pill strong { font-weight: 900; color: #89b4fa; }
    .em-pill.intent { color: #fab387; border-color: #fab387; background: rgba(250,179,135,0.08); font-weight: 900; font-size: 0.65rem; }
    .no-events-sm { font-size: 0.75rem; color: #45475a; font-style: italic; padding: 10px; }
    .sah-meta { font-size: 0.65rem; color: #6c7086; margin-top: 6px; }
    @media (max-width: 768px) {
      .analysis-tabs { overflow-x: auto; }
      .atab { min-width: 60px; font-size: 0.55rem; padding: 10px 4px; }
      .geo-deep-grid { grid-template-columns: 1fr; }
      .mmr-grid { grid-template-columns: repeat(2, 1fr); }
      .rrd-stats { grid-template-columns: repeat(2, 1fr); }
      .perf-summary-row { grid-template-columns: repeat(3, 1fr); }
      .perf-metrics-grid { grid-template-columns: repeat(2, 1fr); }
      .settings-grid { grid-template-columns: repeat(2, 1fr); }
    }

    /* VISUAL R/R DIAGRAM */
    .rr-visual-diagram { background: #0b0b15; border: 1px solid #1f1f3a; border-radius: 8px; padding: 16px; margin: 16px 0; }
    .rrd-header { font-size: 0.55rem; color: #45475a; font-weight: 900; letter-spacing: 1px; margin-bottom: 14px; }
    .rrd-chart { display: flex; flex-direction: column; gap: 0; }
    .rrd-row { display: flex; align-items: center; gap: 10px; }
    .rrd-tag { font-size: 0.55rem; font-weight: 900; padding: 3px 8px; border-radius: 4px; width: 60px; text-align: center; flex-shrink: 0; }
    .tp-tag { background: rgba(166,227,161,0.1); color: #a6e3a1; border: 1px solid rgba(166,227,161,0.3); }
    .entry-tag { background: rgba(137,180,250,0.1); color: #89b4fa; border: 1px solid rgba(137,180,250,0.3); }
    .sl-tag { background: rgba(243,139,168,0.1); color: #f38ba8; border: 1px solid rgba(243,139,168,0.3); }
    .rrd-bar { flex: 1; height: 2px; }
    .tp-bar { background: rgba(166,227,161,0.4); }
    .entry-bar { background: rgba(137,180,250,0.5); height: 3px; }
    .sl-bar { background: rgba(243,139,168,0.4); }
    .rrd-price { font-size: 0.75rem; font-weight: 900; color: #cdd6f4; width: 80px; text-align: right; flex-shrink: 0; }
    .rrd-price.bullish { color: #a6e3a1; }
    .rrd-price.bearish { color: #f38ba8; }
    .reward-row { padding: 5px 70px; }
    .risk-row { padding: 5px 70px; }
    .rrd-amount { font-size: 0.7rem; font-weight: 900; }
    .rrd-amount.bullish { color: #a6e3a1; }
    .rrd-amount.bearish { color: #f38ba8; }
    .rrd-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #1f1f3a; }
    .rrd-stat { display: flex; flex-direction: column; background: #11111b; border-radius: 6px; padding: 8px; text-align: center; }
    .rrd-stat span { font-size: 0.45rem; color: #45475a; font-weight: 900; text-transform: uppercase; margin-bottom: 4px; }
    .rrd-stat strong { font-size: 0.8rem; font-weight: 900; color: #cdd6f4; }
    .rrd-stat strong.bullish { color: #a6e3a1; }

    /* PERFORMANCE TAB */
    .perf-tab-tile { padding: 24px; }
    .perf-summary-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
    .perf-kpi { background: #11111b; border: 1px solid #1f1f3a; border-radius: 8px; padding: 14px; text-align: center; display: flex; flex-direction: column; gap: 4px; }
    .perf-kpi span { font-size: 0.45rem; color: #45475a; font-weight: 900; text-transform: uppercase; letter-spacing: 1px; }
    .perf-kpi strong { font-size: 1.1rem; font-weight: 900; color: #cdd6f4; }
    .perf-kpi strong.bullish { color: #a6e3a1; }
    .perf-metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 14px; }
    .pm-kpi { background: #0b0b15; border: 1px solid #1f1f3a; border-radius: 6px; padding: 10px; text-align: center; }
    .pm-kpi span { display: block; font-size: 0.45rem; color: #45475a; font-weight: 900; margin-bottom: 4px; }
    .pm-kpi strong { font-size: 0.85rem; font-weight: 900; color: #cdd6f4; }
    .pm-kpi strong.bearish { color: #f38ba8; }
    .perf-streaks { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
    .streak-item { font-size: 0.65rem; color: #9399b2; padding: 4px 10px; background: #11111b; border-radius: 100px; border: 1px solid #313244; }
    .streak-item.win { color: #a6e3a1; border-color: rgba(166,227,161,0.3); }
    .streak-item.loss { color: #f38ba8; border-color: rgba(243,139,168,0.3); }
    .recent-trades-header { font-size: 0.55rem; color: #45475a; font-weight: 900; letter-spacing: 1px; margin-bottom: 10px; }
    .recent-trades-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
    .rt-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: #0b0b15; border: 1px solid #1f1f3a; border-radius: 6px; }
    .rt-symbol { font-size: 0.7rem; font-weight: 900; color: #cdd6f4; flex: 1; }
    .rt-pct { font-size: 0.75rem; font-weight: 900; width: 50px; text-align: right; }
    .rt-age { font-size: 0.6rem; color: #45475a; width: 80px; text-align: center; }
    .rt-badge { font-size: 0.5rem; font-weight: 900; padding: 2px 8px; border-radius: 4px; }
    .win-badge { background: rgba(166,227,161,0.1); color: #a6e3a1; border: 1px solid rgba(166,227,161,0.3); }
    .loss-badge { background: rgba(243,139,168,0.1); color: #f38ba8; border: 1px solid rgba(243,139,168,0.3); }
    .perf-actions { display: flex; gap: 8px; flex-wrap: wrap; }

    /* SETTINGS TAB */
    .settings-tab-tile { padding: 24px; }
    .settings-section { margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #1f1f3a; }
    .settings-section:last-of-type { border-bottom: none; }
    .settings-label { font-size: 0.6rem; color: #89b4fa; font-weight: 900; letter-spacing: 1px; margin-bottom: 12px; }
    .settings-actions { display: flex; gap: 8px; flex-wrap: wrap; }
    .settings-btn { padding: 6px 14px; background: #1a1a2a; border: 1px solid #313244; color: #9399b2; font-size: 0.65rem; font-weight: 800; border-radius: 6px; cursor: pointer; transition: all 0.2s; }
    .settings-btn:hover { background: #252535; color: #cdd6f4; border-color: #89b4fa; }
    .settings-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .sg-item { background: #0b0b15; border: 1px solid #1f1f3a; border-radius: 6px; padding: 10px; display: flex; flex-direction: column; gap: 4px; }
    .sg-item span { font-size: 0.45rem; color: #45475a; font-weight: 900; text-transform: uppercase; }
    .sg-item strong { font-size: 0.75rem; font-weight: 900; color: #89b4fa; }
    .settings-toggles { display: flex; flex-direction: column; gap: 6px; }
    .st-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #0b0b15; border: 1px solid #1f1f3a; border-radius: 6px; font-size: 0.65rem; color: #9399b2; }
    .st-on { font-size: 0.6rem; font-weight: 900; color: #a6e3a1; background: rgba(166,227,161,0.08); padding: 2px 8px; border-radius: 4px; }
    .st-off { font-size: 0.6rem; font-weight: 900; color: #45475a; background: #1a1a2a; padding: 2px 8px; border-radius: 4px; }
    .settings-footer-actions { display: flex; gap: 8px; flex-wrap: wrap; padding-top: 8px; }

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

    /* PIVOT INTERPRETATION */
    .pivot-interpretation { margin-top: 16px; padding-top: 14px; border-top: 1px solid #1f1f3a; }
    .pi-bias-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .pi-badge { font-size: 0.55rem; font-weight: 950; letter-spacing: 1px; padding: 3px 10px; border-radius: 4px; }
    .pi-badge.bullish { background: rgba(166,227,161,0.12); color: #a6e3a1; border: 1px solid rgba(166,227,161,0.3); }
    .pi-badge.bearish { background: rgba(243,139,168,0.12); color: #f38ba8; border: 1px solid rgba(243,139,168,0.3); }
    .pi-badge.neutral { background: rgba(137,180,250,0.1); color: #89b4fa; border: 1px solid rgba(137,180,250,0.25); }
    .pi-align-tag { font-size: 0.52rem; font-weight: 900; letter-spacing: 0.5px; }
    .pi-align-tag.aligned { color: #a6e3a1; }
    .pi-align-tag.conflicting { color: #f38ba8; }
    .pi-align-tag.neutral { color: #f9e2af; }
    .pi-read-text { font-size: 0.68rem; color: #a6adc8; line-height: 1.6; margin: 0 0 12px; padding: 10px 12px; background: rgba(17,17,27,0.5); border-left: 3px solid #585b70; border-radius: 0 6px 6px 0; }
    .pi-key-levels { display: flex; gap: 10px; margin-bottom: 10px; }
    .pi-kl { flex: 1; padding: 8px 10px; border-radius: 6px; display: flex; flex-direction: column; gap: 3px; }
    .pi-kl span { font-size: 0.44rem; font-weight: 950; letter-spacing: 1px; text-transform: uppercase; }
    .pi-kl strong { font-size: 0.8rem; font-weight: 950; }
    .pi-kl.res { background: rgba(243,139,168,0.06); border: 1px solid rgba(243,139,168,0.2); }
    .pi-kl.res span { color: #585b70; }
    .pi-kl.res strong { color: #f38ba8; }
    .pi-kl.sup { background: rgba(166,227,161,0.06); border: 1px solid rgba(166,227,161,0.2); }
    .pi-kl.sup span { color: #585b70; }
    .pi-kl.sup strong { color: #a6e3a1; }
    .pi-fib-note { font-size: 0.62rem; color: #cba6f7; background: rgba(203,166,247,0.06); border: 1px solid rgba(203,166,247,0.15); border-radius: 6px; padding: 8px 12px; line-height: 1.5; }

    /* MARKET MOMENTUM READ */
    .momentum-read-section { background: rgba(137,180,250,0.02); }
    .mmr-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; margin-bottom: 12px; }
    .mmr-item { display: flex; flex-direction: column; gap: 4px; background: #0b0b15; border-radius: 6px; padding: 10px; border: 1px solid #1f1f3a; }
    .mmr-lbl { font-size: 0.44rem; font-weight: 950; color: #45475a; letter-spacing: 1px; text-transform: uppercase; }
    .mmr-val { font-size: 1.1rem; font-weight: 950; color: #cdd6f4; line-height: 1; }
    .mmr-val.strong { color: #fab387; }
    .mmr-val.trending { color: #89b4fa; }
    .mmr-val.weak { color: #6c7086; }
    .mmr-val.high { color: #f38ba8; }
    .mmr-val.medium { color: #f9e2af; }
    .mmr-val.low { color: #6c7086; }
    .mmr-interp { font-size: 0.52rem; font-weight: 900; letter-spacing: 0.3px; }
    .mmr-interp.strong { color: #fab387; }
    .mmr-interp.trending { color: #89b4fa; }
    .mmr-interp.weak { color: #6c7086; }
    .mmr-interp.bullish { color: #a6e3a1; }
    .mmr-interp.bearish { color: #f38ba8; }
    .mmr-interp.neutral { color: #f9e2af; }
    .mmr-combined-read { font-size: 0.65rem; color: #a6adc8; line-height: 1.6; padding: 10px 12px; background: rgba(137,180,250,0.04); border-left: 3px solid #89b4fa; border-radius: 0 6px 6px 0; }
    .mmr-plan { margin-top: 12px; background: rgba(17,17,27,0.55); border: 1px solid #1f1f3a; border-radius: 8px; padding: 12px; }
    .mmr-plan-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; font-size: 0.56rem; font-weight: 900; letter-spacing: 0.9px; color: #cdd6f4; }
    .mmr-bias { padding: 3px 8px; border-radius: 10px; font-size: 0.5rem; font-weight: 900; }
    .mmr-bias.bullish { color: #a6e3a1; background: rgba(166,227,161,0.12); border: 1px solid rgba(166,227,161,0.35); }
    .mmr-bias.bearish { color: #f38ba8; background: rgba(243,139,168,0.12); border: 1px solid rgba(243,139,168,0.35); }
    .mmr-bias.neutral { color: #f9e2af; background: rgba(249,226,175,0.12); border: 1px solid rgba(249,226,175,0.35); }
    .mmr-evidence { margin: 0 0 10px; padding-left: 16px; color: #a6adc8; font-size: 0.6rem; line-height: 1.5; }
    .mmr-evidence li { margin-bottom: 4px; }
    .mmr-scenarios { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .mmr-scenario { border-radius: 6px; padding: 10px; border: 1px solid #1f1f3a; background: #0b0b15; }
    .mmr-scenario.bull { border-color: rgba(166,227,161,0.25); background: rgba(166,227,161,0.04); }
    .mmr-scenario.bear { border-color: rgba(243,139,168,0.25); background: rgba(243,139,168,0.04); }
    .sc-title { font-size: 0.48rem; letter-spacing: 1px; font-weight: 900; margin-bottom: 6px; color: #cdd6f4; }
    .sc-row { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 4px; }
    .sc-row span { font-size: 0.46rem; color: #6c7086; letter-spacing: 0.6px; font-weight: 800; }
    .sc-row strong { font-size: 0.64rem; color: #cdd6f4; font-weight: 900; }
    .mmr-plan-note { margin-top: 10px; font-size: 0.58rem; color: #9399b2; line-height: 1.45; border-top: 1px dashed #313244; padding-top: 8px; }

    /* TECH SECTION WRAPPERS */
    .tech-section { padding: 20px 24px; border-bottom: 1px solid #1f1f3a; }
    .tech-section:last-child { border-bottom: none; }
    .action-section { background: transparent; }
    .pivot-section .pm-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 12px; }
    .pivot-section .pm-v { font-size: 0.7rem; font-weight: 800; color: #bac2de; padding: 8px 6px; background: #0b0b15; border-radius: 4px; text-align: center; }
    .pivot-section .pm-v.res { color: #f38ba8; }
    .pivot-section .pm-v.sup { color: #a6e3a1; }
    .pivot-section .pm-v.center { background: rgba(137,180,250,0.1); border: 1px solid #89b4fa; color: #89b4fa; }

    /* AI REASONING SECTION */
    .ai-reasoning-section { background: rgba(137,180,250,0.02); }
    .ai-reasoning-section .tile-header { margin-bottom: 14px; }
    .air-group { margin-bottom: 14px; }
    .air-group-label { font-size: 0.5rem; font-weight: 900; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px; padding: 2px 8px; border-radius: 4px; display: inline-block; }
    .bullish-label { color: #a6e3a1; background: rgba(166,227,161,0.08); border: 1px solid rgba(166,227,161,0.2); }
    .caution-label { color: #f9e2af; background: rgba(249,226,175,0.08); border: 1px solid rgba(249,226,175,0.2); }
    .air-factor { padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; }
    .bullish-factor { background: rgba(166,227,161,0.04); border-left: 2px solid rgba(166,227,161,0.4); }
    .caution-factor { background: rgba(249,226,175,0.04); border-left: 2px solid rgba(249,226,175,0.4); }
    .air-indicator { font-size: 0.68rem; font-weight: 800; color: #cdd6f4; margin-bottom: 3px; }
    .bullish-factor .air-indicator { color: #a6e3a1; }
    .caution-factor .air-indicator { color: #f9e2af; }
    .air-explanation { font-size: 0.6rem; color: #6c7086; line-height: 1.4; }
    .air-range { background: #0b0b15; border: 1px solid #1f1f3a; border-radius: 6px; padding: 10px 14px; margin-top: 12px; margin-bottom: 10px; }
    .air-range-header { font-size: 0.5rem; color: #45475a; font-weight: 900; letter-spacing: 1px; margin-bottom: 8px; }
    .air-range-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px; font-size: 0.65rem; }
    .air-range-row.up .air-dir { color: #a6e3a1; font-weight: 900; }
    .air-range-row.down .air-dir { color: #f38ba8; font-weight: 900; }
    .air-range-text { color: #9399b2; }
    .air-data-line { font-size: 0.5rem; color: #45475a; font-weight: 700; font-family: monospace; letter-spacing: 0.5px; padding: 6px 0; border-top: 1px solid #1f1f3a; margin-top: 4px; }

    /* RISK DUAL PANEL */
    .risk-dual-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-bottom: 1px solid #1f1f3a; }
    .risk-panel-card { padding: 20px 18px; }
    .risk-panel-card:first-child { border-right: 1px solid #1f1f3a; }
    .risk-panel-card .tile-header { margin-bottom: 12px; }
    .risk-panel-card .pic-desc { font-size: 0.62rem; color: #9399b2; margin: 0 0 10px; line-height: 1.4; }

    /* SIGNAL CONFLICT BANNER */
    .signal-conflict-banner { margin-bottom: 20px; border-radius: 8px; padding: 14px 18px; border: 1px solid; }
    .conflict-high { background: rgba(243,139,168,0.06); border-color: rgba(243,139,168,0.4); }
    .conflict-medium { background: rgba(249,226,175,0.06); border-color: rgba(249,226,175,0.3); }
    .scb-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .scb-icon { font-size: 1rem; }
    .scb-title { font-size: 0.55rem; font-weight: 950; letter-spacing: 1.5px; color: #cdd6f4; flex: 1; }
    .scb-badge { font-size: 0.5rem; font-weight: 900; padding: 2px 6px; border-radius: 3px; }
    .conflict-high .scb-badge { background: rgba(243,139,168,0.2); color: #f38ba8; }
    .conflict-medium .scb-badge { background: rgba(249,226,175,0.2); color: #f9e2af; }
    .scb-headline { font-size: 0.7rem; font-weight: 800; color: #cdd6f4; margin-bottom: 6px; line-height: 1.3; }
    .conflict-high .scb-headline { color: #f38ba8; }
    .conflict-medium .scb-headline { color: #f9e2af; }
    .scb-guidance { font-size: 0.62rem; color: #9399b2; line-height: 1.5; margin-bottom: 10px; }
    .scb-triggers { display: flex; gap: 10px; margin-top: 6px; }
    .scb-trigger { font-size: 0.6rem; font-weight: 900; padding: 4px 10px; border-radius: 4px; }
    .scb-trigger.bullish { background: rgba(166,227,161,0.1); color: #a6e3a1; border: 1px solid rgba(166,227,161,0.3); }
    .scb-trigger.bearish { background: rgba(243,139,168,0.1); color: #f38ba8; border: 1px solid rgba(243,139,168,0.3); }

    /* CORRELATION MATRIX ROW */
    .corr-matrix-row { margin-top: 14px; padding-top: 14px; border-top: 1px solid #1f1f3a; }
    .cm-label { font-size: 0.5rem; color: #45475a; font-weight: 900; letter-spacing: 1.2px; margin-bottom: 8px; }
    .cm-cells { display: flex; gap: 8px; margin-bottom: 8px; }
    .cm-cell { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 3px; padding: 8px 6px; border-radius: 6px; border: 1px solid #1f1f3a; background: #0b0b15; }
    .cm-cell span { font-size: 0.5rem; color: #45475a; font-weight: 700; text-transform: uppercase; }
    .cm-cell strong { font-size: 0.8rem; font-weight: 950; }
    .cm-cell.corr-strong-pos strong { color: #a6e3a1; }
    .cm-cell.corr-pos strong { color: #89dceb; }
    .cm-cell.corr-neutral strong { color: #9399b2; }
    .cm-cell.corr-neg strong { color: #fab387; }
    .cm-cell.corr-strong-neg strong { color: #f38ba8; }
    .cm-interpretation { font-size: 0.58rem; color: #6c7086; line-height: 1.4; }

    /* SAMPLE SIZE WARNING */
    .sample-size-warning { margin: 10px 0; padding: 8px 12px; background: rgba(249,226,175,0.07); border: 1px solid rgba(249,226,175,0.3); border-radius: 6px; font-size: 0.62rem; color: #f9e2af; line-height: 1.4; }

    /* MACRO CONTEXT BLOCK (in Risk tab) */
    .macro-context-block { padding: 16px 20px; border-top: 1px solid #1f1f3a; margin-top: 8px; background: rgba(17,17,27,0.4); border-radius: 0 0 8px 8px; }
    .macro-context-block .tile-header { margin-bottom: 10px; }

    /* LEVELS INACTIVE (wait state) */
    .levels-inactive { opacity: 0.45; pointer-events: none; position: relative; }
    .levels-pending { font-size: 0.65rem; color: #f9e2af; background: rgba(249,226,175,0.08); border: 1px solid rgba(249,226,175,0.25); border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; }

    /* ACTION REC BADGE */
    .action-rec-badge { font-size: 0.5rem; font-weight: 900; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 1px; }
    .action-rec-badge.bullish { background: rgba(166,227,161,0.15); color: #a6e3a1; border: 1px solid rgba(166,227,161,0.3); }
    .action-rec-badge.bearish { background: rgba(243,139,168,0.15); color: #f38ba8; border: 1px solid rgba(243,139,168,0.3); }
    .action-rec-badge.badge-wait { background: rgba(249,226,175,0.1); color: #f9e2af; border: 1px solid rgba(249,226,175,0.3); }
    .action-rec-badge.neutral { background: rgba(108,112,134,0.15); color: #9399b2; border: 1px solid rgba(108,112,134,0.3); }

    /* CONFLICT BADGE ON STATUS PILL */
    .th-conflict-badge { font-size: 0.45rem; font-weight: 900; padding: 2px 6px; border-radius: 3px; letter-spacing: 0.5px; }
    .th-conflict-badge.sev-high { background: rgba(243,139,168,0.2); color: #f38ba8; border: 1px solid rgba(243,139,168,0.4); }
    .th-conflict-badge.sev-medium { background: rgba(249,226,175,0.2); color: #f9e2af; border: 1px solid rgba(249,226,175,0.3); }

    /* PERFORMANCE TAB */
    .perf-content { padding: 20px 24px; display: flex; flex-direction: column; gap: 20px; }
    .perf-chart-area { background: #000; border-radius: 8px; overflow: hidden; }
    .perf-chart-area .tile-header { padding: 12px 16px; background: #0b0b15; margin-bottom: 0; border-bottom: 1px solid #1f1f3a; }
    .perf-chart-area .terminal-chart-area { height: 360px; }
    .chart-placeholder { display: flex; align-items: center; justify-content: center; height: 200px; color: #45475a; font-size: 0.75rem; }

    /* MUTED CORRELATION TEXT */
    .ch-correlation.muted { color: #45475a; font-style: italic; }

    /* SECONDARY BACKTEST GRID */
    .pb2-grid-secondary { margin-top: 6px; padding-top: 8px; border-top: 1px solid #1f1f3a; }

    /* PRE-EVENT ALERT BANNER */
    .pre-event-alert { margin: 16px 0; padding: 12px 16px; border-radius: 8px; border: 1px solid; }
    .pea-active { background: rgba(243,139,168,0.07); border-color: rgba(243,139,168,0.5); }
    .pea-caution { background: rgba(249,226,175,0.07); border-color: rgba(249,226,175,0.4); }
    .pea-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .pea-title { font-size: 0.55rem; font-weight: 950; letter-spacing: 1.5px; flex: 1; }
    .pea-active .pea-title { color: #f38ba8; }
    .pea-caution .pea-title { color: #f9e2af; }
    .pea-countdown { font-size: 0.6rem; font-weight: 900; padding: 2px 8px; border-radius: 4px; }
    .pea-active .pea-countdown { background: rgba(243,139,168,0.15); color: #f38ba8; }
    .pea-caution .pea-countdown { background: rgba(249,226,175,0.15); color: #f9e2af; }
    .pea-body { font-size: 0.62rem; color: #9399b2; line-height: 1.5; margin-bottom: 6px; }
    .pea-event { font-size: 0.6rem; color: #cdd6f4; font-weight: 700; margin-bottom: 6px; }
    .pea-multiplier { font-size: 0.58rem; color: #6c7086; }
    .pea-multiplier strong { color: #cba6f7; }

    /* VOLUME PROFILE */
    .vp-key-levels { display: flex; gap: 8px; margin-bottom: 14px; }
    .vp-lvl { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 8px; background: #0b0b15; border-radius: 6px; border: 1px solid #1f1f3a; }
    .vp-lvl span { font-size: 0.5rem; color: #45475a; font-weight: 900; text-transform: uppercase; }
    .vp-lvl strong { font-size: 0.75rem; font-weight: 950; margin-top: 3px; color: #cdd6f4; }
    .vp-lvl.poc { border-color: #cba6f7; }
    .vp-lvl.poc strong { color: #cba6f7; }
    .vp-sparkline { display: flex; flex-direction: column; gap: 2px; margin-bottom: 10px; max-height: 140px; overflow-y: auto; }
    .vp-bar-row { display: flex; align-items: center; gap: 6px; }
    .vp-price { font-size: 0.45rem; color: #45475a; width: 40px; text-align: right; font-family: monospace; }
    .vp-bar-track { flex: 1; height: 6px; background: #0b0b15; border-radius: 3px; overflow: hidden; }
    .vp-bar-fill { height: 100%; background: rgba(137,180,250,0.35); border-radius: 3px; transition: width 0.3s; }
    .vp-bar-fill.poc-bar { background: #cba6f7; }
    .vp-interpretation { font-size: 0.6rem; color: #6c7086; line-height: 1.4; margin: 0; }

    /* SESSION VWAP */
    .vwap-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-bottom: 10px; }
    .vwap-cell { display: flex; flex-direction: column; align-items: center; padding: 8px 4px; background: #0b0b15; border-radius: 6px; border: 1px solid #1f1f3a; }
    .vwap-cell span { font-size: 0.45rem; color: #45475a; font-weight: 900; text-transform: uppercase; }
    .vwap-cell strong { font-size: 0.7rem; font-weight: 950; margin-top: 3px; }
    .vwap-position-badge { display: inline-block; font-size: 0.55rem; font-weight: 900; padding: 3px 10px; border-radius: 4px; margin-bottom: 8px; letter-spacing: 1px; }
    .vwap-position-badge.above { background: rgba(166,227,161,0.1); color: #a6e3a1; border: 1px solid rgba(166,227,161,0.3); }
    .vwap-position-badge.below { background: rgba(243,139,168,0.1); color: #f38ba8; border: 1px solid rgba(243,139,168,0.3); }
    .vwap-position-badge.extended { background: rgba(249,226,175,0.1); color: #f9e2af; border: 1px solid rgba(249,226,175,0.3); }
    .vwap-interpretation { font-size: 0.6rem; color: #6c7086; line-height: 1.4; margin: 0; }

    /* LIQUIDITY MAP */
    .liquidity-map-section { padding: 20px; border-top: 1px solid #1f1f3a; }
    .lm-dual { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 12px 0; }
    .lm-col-header { font-size: 0.5rem; font-weight: 950; letter-spacing: 1.5px; padding: 4px 8px; border-radius: 3px; margin-bottom: 8px; }
    .lm-col-header.bearish { background: rgba(243,139,168,0.1); color: #f38ba8; }
    .lm-col-header.bullish { background: rgba(166,227,161,0.1); color: #a6e3a1; }
    .lm-level { display: flex; align-items: center; gap: 6px; padding: 6px 8px; border-radius: 5px; margin-bottom: 4px; background: #0b0b15; border: 1px solid #1f1f3a; }
    .lm-price { font-size: 0.68rem; font-weight: 900; flex: 1; }
    .lm-dist { font-size: 0.55rem; color: #6c7086; }
    .lm-badge { font-size: 0.45rem; font-weight: 900; padding: 2px 5px; border-radius: 3px; text-transform: uppercase; }
    .strength-strong .lm-badge { background: rgba(249,226,175,0.2); color: #f9e2af; }
    .strength-moderate .lm-badge { background: rgba(137,180,250,0.1); color: #89b4fa; }
    .strength-weak .lm-badge { background: rgba(69,71,90,0.3); color: #6c7086; }
    .lm-interpretation { font-size: 0.6rem; color: #6c7086; line-height: 1.4; margin: 0; }

    /* BLOCK FLOW */
    .block-flow-section { padding: 20px; border-top: 1px solid #1f1f3a; }
    .bf-quiet { opacity: 0.7; }
    .bf-quiet-msg { font-size: 0.62rem; color: #6c7086; line-height: 1.4; margin: 8px 0 0; }
    .bf-summary { display: flex; align-items: center; gap: 12px; margin: 10px 0; }
    .bf-direction { font-size: 0.6rem; font-weight: 950; padding: 4px 12px; border-radius: 5px; letter-spacing: 1px; }
    .bf-dir-bullish { background: rgba(166,227,161,0.1); color: #a6e3a1; border: 1px solid rgba(166,227,161,0.3); }
    .bf-dir-bearish { background: rgba(243,139,168,0.1); color: #f38ba8; border: 1px solid rgba(243,139,168,0.3); }
    .bf-dir-neutral { background: rgba(69,71,90,0.3); color: #9399b2; border: 1px solid #313244; }
    .bf-counts { display: flex; gap: 10px; font-size: 0.6rem; font-weight: 700; }
    .bf-events { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }
    .bf-event { display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 5px; background: #0b0b15; border: 1px solid #1f1f3a; }
    .bf-bullish { border-left: 2px solid rgba(166,227,161,0.5); }
    .bf-bearish { border-left: 2px solid rgba(243,139,168,0.5); }
    .bf-ts { font-size: 0.5rem; color: #45475a; font-family: monospace; }
    .bf-p { font-size: 0.65rem; font-weight: 800; flex: 1; }
    .bf-vol { font-size: 0.55rem; color: #cba6f7; font-weight: 700; }
    .bf-interpretation { font-size: 0.58rem; color: #6c7086; line-height: 1.4; margin: 0; }

    /* GEOPOLITICAL RISK INTELLIGENCE */
    .geo-risk-section { padding: 20px; border-top: 1px solid #1f1f3a; border-left: 4px solid #6c7086; }
    .geo-risk-section.geo-low      { border-left-color: #a6e3a1; background: rgba(166,227,161,0.03); }
    .geo-risk-section.geo-moderate { border-left-color: #f9e2af; background: rgba(249,226,175,0.04); }
    .geo-risk-section.geo-high     { border-left-color: #fab387; background: rgba(250,179,135,0.05); }
    .geo-risk-section.geo-critical { border-left-color: #f38ba8; background: rgba(243,139,168,0.06); }

    .geo-risk-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
    .geo-risk-title  { display: flex; align-items: center; gap: 6px; font-size: 0.55rem; font-weight: 950; letter-spacing: 1.5px; color: #89b4fa; }
    .geo-risk-icon   { font-size: 0.9rem; }

    .geo-risk-score-badge { display: flex; align-items: baseline; gap: 3px; padding: 4px 10px; border-radius: 20px; background: rgba(137,180,250,0.1); border: 1px solid rgba(137,180,250,0.2); }
    .geo-score-val   { font-size: 1.1rem; font-weight: 900; color: #cdd6f4; }
    .geo-score-label { font-size: 0.55rem; color: #6c7086; }
    .geo-risk-level  { font-size: 0.5rem; font-weight: 950; letter-spacing: 1.5px; padding: 2px 6px; border-radius: 3px; margin-left: 4px; }
    .geo-low    .geo-risk-level { background: rgba(166,227,161,0.15); color: #a6e3a1; }
    .geo-moderate .geo-risk-level { background: rgba(249,226,175,0.15); color: #f9e2af; }
    .geo-high   .geo-risk-level { background: rgba(250,179,135,0.15); color: #fab387; }
    .geo-critical .geo-risk-level { background: rgba(243,139,168,0.15); color: #f38ba8; }

    .geo-keywords { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px; }
    .geo-kw-tag { font-size: 0.48rem; font-weight: 700; letter-spacing: 0.8px; padding: 3px 8px; border-radius: 3px; background: rgba(203,166,247,0.1); border: 1px solid rgba(203,166,247,0.25); color: #cba6f7; text-transform: uppercase; }

    .geo-impact-row  { display: grid; grid-template-columns: repeat(3,1fr); gap: 8px; margin-bottom: 14px; }
    .geo-impact-cell { background: rgba(30,30,46,0.6); border: 1px solid #313244; border-radius: 6px; padding: 8px 10px; display: flex; flex-direction: column; gap: 4px; }
    .geo-cell-label  { font-size: 0.45rem; font-weight: 950; letter-spacing: 1.5px; color: #6c7086; }
    .geo-cell-val    { font-size: 0.65rem; font-weight: 800; color: #cdd6f4; }
    .geo-cell-val.bullish { color: #a6e3a1; }
    .geo-cell-val.bearish { color: #f38ba8; }
    .geo-cell-val.neutral { color: #f9e2af; }
    .geo-cell-val.geo-confirmed { color: #a6e3a1; }
    .geo-cell-val.geo-diverging  { color: #f38ba8; }
    .geo-cell-val.geo-early      { color: #f9e2af; }
    .geo-cell-val.geo-none       { color: #6c7086; }

    .geo-indicators { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
    .geo-ind-row     { display: flex; align-items: flex-start; gap: 8px; padding: 8px 10px; border-radius: 6px; border: 1px solid transparent; }
    .geo-ind-confirming { background: rgba(166,227,161,0.05); border-color: rgba(166,227,161,0.2); }
    .geo-ind-diverging  { background: rgba(243,139,168,0.05); border-color: rgba(243,139,168,0.2); }
    .geo-ind-neutral    { background: rgba(249,226,175,0.04); border-color: rgba(249,226,175,0.15); }
    .geo-ind-icon    { font-size: 0.75rem; flex-shrink: 0; margin-top: 1px; }
    .geo-ind-content { display: flex; flex-direction: column; gap: 2px; }
    .geo-ind-name    { font-size: 0.5rem; font-weight: 950; letter-spacing: 1px; color: #89b4fa; }
    .geo-ind-desc    { font-size: 0.58rem; color: #a6adc8; line-height: 1.35; }

    .geo-narrative { font-size: 0.62rem; color: #cdd6f4; line-height: 1.6; padding: 10px 12px; background: rgba(17,17,27,0.5); border-radius: 6px; border-left: 3px solid #89b4fa; margin-bottom: 12px; }

    .geo-action-bias { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 6px; }
    .geo-action-trade   { background: rgba(166,227,161,0.1); border: 1px solid rgba(166,227,161,0.3); }
    .geo-action-reduce  { background: rgba(243,139,168,0.1); border: 1px solid rgba(243,139,168,0.3); }
    .geo-action-wait    { background: rgba(249,226,175,0.08); border: 1px solid rgba(249,226,175,0.25); }
    .geo-action-monitor { background: rgba(137,180,250,0.07); border: 1px solid rgba(137,180,250,0.2); }
    .geo-action-label { font-size: 0.45rem; font-weight: 950; letter-spacing: 1.5px; color: #6c7086; }
    .geo-action-val   { font-size: 0.6rem; font-weight: 900; letter-spacing: 0.5px; }
    .geo-action-trade   .geo-action-val { color: #a6e3a1; }
    .geo-action-reduce  .geo-action-val { color: #f38ba8; }
    .geo-action-wait    .geo-action-val { color: #f9e2af; }
    .geo-action-monitor .geo-action-val { color: #89b4fa; }

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
      .th-symbol { font-size: 1.3rem; }
      .th-price { font-size: 0.95rem; }
      .th-change { font-size: 0.7rem; }
      .aph-text { font-size: 1.2rem; }
      .lvl-box { padding: 6px; min-width: 0; }
      .lv { font-size: 0.72rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .deep-grid { grid-template-columns: 1fr; }
      .risk-dual-panel { grid-template-columns: 1fr; }
      .risk-panel-card:first-child { border-right: none; border-bottom: 1px solid #1f1f3a; }
      .tech-section { padding: 16px; }
      .levels-stack { align-items: flex-start; }
    }

    @keyframes pulse { 0% { opacity: 0.8; } 50% { opacity: 1; } 100% { opacity: 0.8; } }
  `]
})
export class InstrumentCardComponent implements OnChanges {
  riskMultiplier = 1.0;
  intelTab: 'macro' | 'micro' | 'context' | 'news' = 'macro';

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

  getTopVPBuckets() {
    const vp = this.analysis.volume_profile;
    if (!vp?.buckets?.length) return [];
    const buckets = [...vp.buckets];
    const sorted = buckets.sort((a, b) => {
      const midA = (a.price_low + a.price_high) / 2;
      const midB = (b.price_low + b.price_high) / 2;
      return midA - midB;
    });
    const step = Math.max(1, Math.floor(sorted.length / 12));
    const sampled = sorted.filter((_, i) => i % step === 0 || sorted[i].is_poc);
    return sampled.slice(-12);
  }

  getVWAPPositionClass(): string {
    const pos = this.analysis.session_vwap?.position || '';
    if (pos.includes('EXTENDED')) return 'extended';
    if (pos.includes('ABOVE')) return 'above';
    return 'below';
  }

  getEventCountdown(minutes: number | undefined | null): string {
    if (!minutes) return '';
    if (minutes < 60) return `${minutes}m`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  }

  getCorrCellClass(val: number | undefined | null): string {
    if (val === null || val === undefined) return 'corr-neutral';
    if (val >= 0.6) return 'corr-strong-pos';
    if (val >= 0.3) return 'corr-pos';
    if (val > -0.3) return 'corr-neutral';
    if (val > -0.6) return 'corr-neg';
    return 'corr-strong-neg';
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

  // ── Scaling Interpretation Methods ────────────────────────────────────────
  /** Parse dollar target string (e.g. "$75.28") to number, or null */
  private parseTargetPrice(target: string): number | null {
    if (!target || !target.startsWith('$')) return null;
    return parseFloat(target.replace('$', ''));
  }

  getTargetDistance(target: string): string {
    const t = this.parseTargetPrice(target);
    if (t === null) return '';
    const price = this.analysis.current_price;
    const dist = ((Math.abs(t - price) / price) * 100).toFixed(2);
    const direction = this.isBullish ? t > price : t < price;
    const arrow = direction ? '↑' : '↓ (crossed)';
    return `${dist}% ${arrow}`;
  }

  isTargetHit(target: string): boolean {
    const t = this.parseTargetPrice(target);
    if (t === null) return false;
    const price = this.analysis.current_price;
    return this.isBullish ? price >= t : price <= t;
  }

  isNextTarget(target: string): boolean {
    const steps = this.getScalingStrategy();
    const nextUnhit = steps.find(s => !this.isTargetHit(s.target));
    return nextUnhit ? nextUnhit.target === target : false;
  }

  getScalingActionRead(): string {
    const vr = this.analysis.volatility_risk;
    const price = this.analysis.current_price;
    if (!vr) return '';

    const tp1 = vr.take_profit_level1;
    const tp2 = vr.take_profit_level2;
    const tp3 = vr.take_profit;
    const sl = vr.stop_loss;
    const distPct = (t: number) => ((Math.abs(t - price) / price) * 100).toFixed(2);

    if (this.isBullish) {
      if (tp3 && price >= tp3) return `🎯 All three targets hit. Consider closing the 20% runner or raising stop to lock in full profit.`;
      if (tp2 && price >= tp2) return `✅ T1 & T2 hit. 20% runner in play — raise stop to T1 ($${tp1?.toFixed(2) ?? '?'}) to protect gains. Let the runner breathe.`;
      if (tp1 && price >= tp1) return `✅ T1 hit at $${tp1.toFixed(2)}. Exit 50% now. Move stop-loss to breakeven. Target T2 ($${tp2?.toFixed(2) ?? '?'}) with the remaining position.`;
      if (tp1) return `⏳ ${distPct(tp1)}% from T1 ($${tp1.toFixed(2)}). Hold long — do not move stop until T1 is reached. On T1 hit: exit 50%, raise stop, target T2 ($${tp2?.toFixed(2) ?? '?'}).`;
      return `⏳ Target $${tp3.toFixed(2)} (${distPct(tp3)}% away). Hold long with stop at $${sl.toFixed(2)}.`;
    } else {
      if (tp3 && price <= tp3) return `🎯 All three targets hit. Consider closing the 20% runner or lowering stop to lock in full profit.`;
      if (tp2 && price <= tp2) return `✅ T1 & T2 hit. 20% runner in play — lower stop to T1 ($${tp1?.toFixed(2) ?? '?'}) to protect gains.`;
      if (tp1 && price <= tp1) return `✅ T1 hit at $${tp1.toFixed(2)}. Exit 50% now. Move stop-loss to breakeven. Target T2 ($${tp2?.toFixed(2) ?? '?'}) short.`;
      if (tp1) return `⏳ ${distPct(tp1)}% from T1 ($${tp1.toFixed(2)}). Hold short — do not move stop until T1 is reached. On T1 hit: cover 50%, lower stop, target T2 ($${tp2?.toFixed(2) ?? '?'}).`;
      return `⏳ Target $${tp3.toFixed(2)} (${distPct(tp3)}% away). Hold short with stop at $${sl.toFixed(2)}.`;
    }
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
  activeAnalysisTab: 'technical' | 'risk' | 'performance' = 'technical';
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

  getFilteredSummary(): string {
    const text = this.analysis?.trade_signal?.executive_summary ?? '';
    return text
      .split(/(?<=[.!?])\s+/)
      .filter(sentence => {
        const lower = sentence.toLowerCase();
        return !(
          lower.includes('warning:') ||
          (lower.includes('economic') && (lower.includes('event') || lower.includes('news'))) ||
          lower.includes('high-impact event') ||
          lower.includes('volatility is expected') ||
          lower.includes('pre-event') ||
          lower.includes('reduce position') && lower.includes('event')
        );
      })
      .join(' ')
      .trim();
  }

  isWaitAction(): boolean {
    const action = this.analysis?.trade_signal?.action_plan?.toLowerCase() ?? '';
    return action.includes('wait') || action.includes('observe') || action.includes('sideline') || action.includes('neutral');
  }

  getGeoImpactClass(impact: string): string {
    const i = impact.toLowerCase();
    if (i.includes('bullish')) return 'bullish';
    if (i.includes('bearish')) return 'bearish';
    return 'neutral';
  }

  getGeoConfirmationClass(confirmation: string): string {
    switch (confirmation) {
      case 'CONFIRMED': return 'geo-confirmed';
      case 'DIVERGING':  return 'geo-diverging';
      case 'EARLY':      return 'geo-early';
      default:           return 'geo-none';
    }
  }

  getGeoActionClass(bias: string): string {
    const b = bias.toUpperCase();
    if (b.includes('TRADE WITH')) return 'geo-action-trade';
    if (b.includes('REDUCE'))     return 'geo-action-reduce';
    if (b.includes('WAIT'))       return 'geo-action-wait';
    return 'geo-action-monitor';
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

  getReasonImpactClass(reason: string): string {
    const lowerReason = reason.toLowerCase();
    
    // Positive indicators
    if (lowerReason.includes('bullish') || lowerReason.includes('positive') || 
        lowerReason.includes('strength') || lowerReason.includes('momentum') ||
        lowerReason.includes('breakout') || lowerReason.includes('support') ||
        lowerReason.includes('leader') || lowerReason.includes('buy') ||
        lowerReason.includes('opportunity') || lowerReason.includes('boost')) {
      return 'positive';
    }
    
    // Negative indicators  
    if (lowerReason.includes('bearish') || lowerReason.includes('negative') ||
        lowerReason.includes('weak') || lowerReason.includes('resistance') ||
        lowerReason.includes('extended') || lowerReason.includes('overbought') ||
        lowerReason.includes('oversold') || lowerReason.includes('sell') ||
        lowerReason.includes('risk') || lowerReason.includes('caution') ||
        lowerReason.includes('warning') || lowerReason.includes('laggard')) {
      return 'negative';
    }
    
    // Warning/neutral indicators
    if (lowerReason.includes('unclear') || lowerReason.includes('mixed') ||
        lowerReason.includes('conflicting') || lowerReason.includes('wait') ||
        lowerReason.includes('sideways') || lowerReason.includes('neutral') ||
        lowerReason.includes('consolidation') || lowerReason.includes('range')) {
      return 'neutral';
    }
    
    // Informational indicators
    if (lowerReason.includes('adx') || lowerReason.includes('rsi') ||
        lowerReason.includes('volume') || lowerReason.includes('price') ||
        lowerReason.includes('trend') || lowerReason.includes('news') ||
        lowerReason.includes('sentiment') || lowerReason.includes('high')) {
      return 'info';
    }
    
    // Default to neutral for unknown reasons
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

  // ── Enhanced Pullback Analysis Methods ───────────────────────────────────────
  hasPullbackReasons(): boolean {
    return !!(this.analysis.pullback_warning?.reasons && this.analysis.pullback_warning.reasons.length > 0);
  }

  getPullbackReasonClass(reason: string): string {
    const lowerReason = reason.toLowerCase();
    if (lowerReason.includes('extended') || lowerReason.includes('overbought')) return 'high-risk';
    if (lowerReason.includes('warning') || lowerReason.includes('caution')) return 'medium-risk';
    return 'low-risk';
  }

  getPullbackRiskLevel(): string {
    if (!this.analysis.pullback_warning) return 'LOW';
    if (this.analysis.pullback_warning.is_warning) return 'HIGH';
    return 'MODERATE';
  }

  getPullbackRiskClass(): string {
    const level = this.getPullbackRiskLevel();
    return level.toLowerCase();
  }

  getPullbackPosition(): string {
    const price = this.analysis.current_price;
    const stop = this.analysis.volatility_risk?.stop_loss;
    const target = this.analysis.volatility_risk?.take_profit;
    
    if (!stop || !target) return 'UNKNOWN';
    
    const totalRange = target - stop;
    const currentPosition = ((price - stop) / totalRange) * 100;
    
    if (currentPosition < 25) return 'NEAR STOP';
    if (currentPosition > 75) return 'NEAR TARGET';
    return 'MID-RANGE';
  }

  getPullbackAction(): string {
    if (!this.analysis.pullback_warning?.is_warning) return 'HOLD POSITION';
    return 'WAIT FOR ENTRY';
  }

  // ── Technical Heat Analysis Methods ───────────────────────────────────────────
  getADXInterpretation(): string {
    const adx = this.analysis.daily_strength.adx;
    if (adx > 50) return 'Strong Trend';
    if (adx > 25) return 'Trending';
    if (adx > 20) return 'Developing';
    return 'Weak/Range';
  }

  getRSIInterpretation(): string {
    const rsi = this.analysis.daily_strength.rsi;
    if (rsi > 70) return 'Overbought';
    if (rsi > 60) return 'Strong';
    if (rsi < 30) return 'Oversold';
    if (rsi < 40) return 'Weak';
    return 'Neutral';
  }

  getTechnicalHeatImpact(): string {
    const adx = this.analysis.daily_strength.adx;
    const rsi = this.analysis.daily_strength.rsi;
    
    // High ADX + Extreme RSI = High impact
    if (adx > 40 && (rsi > 70 || rsi < 30)) return 'HIGH';
    // Strong trend + moderate RSI = Medium impact
    if (adx > 25 && rsi > 40 && rsi < 60) return 'MEDIUM';
    return 'LOW';
  }

  getTechnicalHeatClass(): string {
    const impact = this.getTechnicalHeatImpact().toLowerCase();
    return impact;
  }

  getTechnicalRecommendation(): string {
    const adx = this.analysis.daily_strength.adx;
    const rsi = this.analysis.daily_strength.rsi;
    
    if (adx > 50 && rsi > 60) return 'Trend Following';
    if (adx > 50 && rsi < 40) return 'Potential Reversal';
    if (rsi > 70) return 'Wait for Pullback';
    if (rsi < 30) return 'Consider Entry';
    return 'Monitor Closely';
  }

  // ── Enhanced Risk Intelligence Methods ───────────────────────────────────────────
  getVolatilityLevel(): string {
    const atr = this.analysis.volatility_risk?.atr;
    if (!atr) return 'UNKNOWN';
    if (atr > this.analysis.current_price * 0.05) return 'HIGH';
    if (atr > this.analysis.current_price * 0.03) return 'MODERATE';
    return 'LOW';
  }

  getVolatilityCheck(): string {
    const level = this.getVolatilityLevel().toLowerCase();
    return level === 'high' ? 'fail' : level === 'moderate' ? 'warn' : 'pass';
  }

  getVolatilityCorrelation(): string {
    const level = this.getVolatilityLevel();
    return `Volatility ${level.toLowerCase()} affects position sizing and risk management`;
  }

  getVolumeStatus(): string {
    // This would need volume data from the analysis
    return 'ANALYZING'; // Placeholder
  }

  getLevelStatus(): string {
    const price = this.analysis.current_price;
    const pp = this.analysis.technical_indicators?.pivot_points;
    
    if (!pp) return 'UNKNOWN';
    
    const { pivot, s1, s2, r1, r2 } = pp;
    if (price > r1) return 'ABOVE R1';
    if (price > pivot) return 'ABOVE PIVOT';
    if (price > s1) return 'ABOVE S1';
    if (price > s2) return 'ABOVE S2';
    return 'BELOW S2';
  }

  getSupportResistanceCheck(): string {
    const status = this.getLevelStatus();
    return status.includes('ABOVE') ? 'pass' : 'warn';
  }

  getLevelCorrelation(): string {
    const status = this.getLevelStatus();
    return `Price positioned ${status.toLowerCase()} - key levels identified`;
  }

  getCorrelationStatus(): string {
    // This would need correlation data
    return 'ANALYZING'; // Placeholder
  }

  getVolatilityRegimeCheck(): string {
    const label = (this.analysis.volatility_risk.volatility_regime_label || '').toLowerCase();
    if (label.includes('extreme') || label.includes('very high')) return 'fail';
    if (label.includes('high') || label.includes('elevated') || label.includes('moderate')) return 'warn';
    return 'pass';
  }

  getVWAPDistLabel(): string {
    const dist = this.analysis.daily_strength.vwap_dist_pct;
    if (dist === undefined || dist === null) return 'N/A';
    if (dist > 1.5) return 'Extended Above';
    if (dist < -1.5) return 'Extended Below';
    return 'Near VWAP';
  }

  getCorrelationRisk(): string {
    return 'Market correlation analysis in progress';
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


  // ── Pivot Interpretation Methods ──────────────────────────────────────────
  getPivotBias(): string {
    const pp = this.analysis.technical_indicators?.pivot_points;
    if (!pp) return 'neutral';
    const price = this.analysis.current_price;
    if (price > pp.r1) return 'bullish';
    if (price > pp.pivot) return 'bullish';
    return 'bearish';
  }

  getPricePosition(): string {
    const pp = this.analysis.technical_indicators?.pivot_points;
    if (!pp) return 'N/A';
    const price = this.analysis.current_price;
    if (price > pp.r3) return 'ABOVE R3';
    if (price > pp.r2) return 'ABOVE R2';
    if (price > pp.r1) return 'ABOVE R1';
    if (price > pp.pivot) return 'ABOVE PIVOT';
    if (price > pp.s1) return 'BELOW PIVOT';
    if (price > pp.s2) return 'AT S1 ZONE';
    if (price > pp.s3) return 'AT S2 ZONE';
    return 'BELOW S3';
  }

  getPivotSignalAlign(): string {
    const bias = this.getPivotBias();
    const signal = this.analysis.trade_signal.recommendation;
    if (bias === signal) return '✓ ALIGNED';
    if (signal === 'neutral') return '— NEUTRAL SIGNAL';
    return '⚠ CONFLICTING';
  }

  getPivotSignalAlignClass(): string {
    const align = this.getPivotSignalAlign();
    if (align.startsWith('✓')) return 'aligned';
    if (align.startsWith('⚠')) return 'conflicting';
    return 'neutral';
  }

  getNearestResistance(): string {
    const pp = this.analysis.technical_indicators?.pivot_points;
    if (!pp) return 'N/A';
    const price = this.analysis.current_price;
    if (price < pp.pivot) return pp.pivot.toFixed(2);
    if (price < pp.r1) return pp.r1.toFixed(2);
    if (price < pp.r2) return pp.r2.toFixed(2);
    return pp.r3.toFixed(2);
  }

  getNearestSupport(): string {
    const pp = this.analysis.technical_indicators?.pivot_points;
    if (!pp) return 'N/A';
    const price = this.analysis.current_price;
    if (price > pp.pivot) return pp.pivot.toFixed(2);
    if (price > pp.s1) return pp.s1.toFixed(2);
    if (price > pp.s2) return pp.s2.toFixed(2);
    return pp.s3.toFixed(2);
  }

  getPivotTradeRead(): string {
    const pp = this.analysis.technical_indicators?.pivot_points;
    if (!pp) return '';
    const price = this.analysis.current_price;
    const signal = this.analysis.trade_signal.recommendation;
    const { pivot, s1, s2, r1, r2, r3 } = pp;

    if (price > r2) {
      return `Price is extended above R2 ($${r2.toFixed(2)}). Consider taking partial profits. A pullback to R1 ($${r1.toFixed(2)}) is healthy — re-enter if trend holds.`;
    }
    if (price > r1) {
      return `Strong bullish momentum above R1 ($${r1.toFixed(2)}). Hold longs and target R2 ($${r2.toFixed(2)}). Trail stop-loss to just below R1 to protect gains.`;
    }
    if (price > pivot) {
      if (signal === 'bearish') {
        return `Price is above Pivot ($${pivot.toFixed(2)}) but signal is bearish — caution. Wait for price to break below Pivot before considering shorts. Target S1 ($${s1.toFixed(2)}).`;
      }
      return `Price above Pivot ($${pivot.toFixed(2)}) confirms bullish bias. Target R1 ($${r1.toFixed(2)}) on continuation. Stop-loss below S1 ($${s1.toFixed(2)}) on long entries.`;
    }
    if (price > s1) {
      if (signal === 'bullish') {
        return `Price below Pivot ($${pivot.toFixed(2)}) — wait for reclaim before going long. A Pivot break above would target R1 ($${r1.toFixed(2)}). S1 ($${s1.toFixed(2)}) is your downside risk.`;
      }
      return `Bearish bias below Pivot ($${pivot.toFixed(2)}). S1 ($${s1.toFixed(2)}) is current support. A break below S1 opens S2 ($${s2.toFixed(2)}) as next target.`;
    }
    if (price > s2) {
      return `Price at S1 support zone ($${s1.toFixed(2)}) — critical make-or-break level. A bounce here targets Pivot ($${pivot.toFixed(2)}). A close below S1 signals further decline to S2 ($${s2.toFixed(2)}).`;
    }
    return `Price below S2 ($${s2.toFixed(2)}) — extended bearish move. High risk for new longs. Wait for S2 reclaim and stabilization before considering long positions.`;
  }

  getFibZoneRead(): string {
    const fib = this.analysis.technical_indicators?.fibonacci;
    if (!fib) return '';
    const price = this.analysis.current_price;
    const r382 = fib.ret_382, r618 = fib.ret_618, e1618 = fib.ext_1618;
    if (!r382 || !r618) return '';
    const pct = (v: number) => Math.abs((price - v) / price) * 100;
    if (pct(r382) < 0.5) return `🎯 At Fib 38.2% ($${r382.toFixed(2)}) — ideal pullback entry zone in an uptrend.`;
    if (pct(r618) < 0.5) return `⚡ At Fib 61.8% ($${r618.toFixed(2)}) — the golden ratio. Last major support before reversal risk increases significantly.`;
    if (e1618 && price > e1618) return `📈 Beyond 1.618 extension ($${e1618.toFixed(2)}) — highly extended. Manage risk and consider partial profit-taking.`;
    if (price < r382 && price > r618) return `In consolidation zone between 38.2% ($${r382.toFixed(2)}) and 61.8% ($${r618.toFixed(2)}) retracement. Wait for directional breakout.`;
    return '';
  }

  // ── Market Momentum Read Methods ──────────────────────────────────────────
  getADXClass(): string {
    const adx = this.analysis.daily_strength.adx;
    if (adx > 50) return 'strong';
    if (adx > 25) return 'trending';
    return 'weak';
  }

  getRSIClass(): string {
    const rsi = this.analysis.daily_strength.rsi;
    if (rsi > 70) return 'bearish';
    if (rsi > 60) return 'bullish';
    if (rsi < 30) return 'bullish';
    if (rsi < 40) return 'bearish';
    return 'neutral';
  }

  getMarketMomentumRead(): string {
    const adx = this.analysis.daily_strength.adx;
    const rsi = this.analysis.daily_strength.rsi;
    const signal = this.analysis.trade_signal.recommendation;

    if (adx > 50 && rsi > 65) return `Strong trending market with elevated momentum. Trend-following entries are favored — avoid counter-trend trades.`;
    if (adx > 50 && rsi < 35) return `Strong trend but RSI is exhausted. A short-term bounce is likely. Wait for RSI to reset above 40 before entering in trend direction.`;
    if (adx > 50 && rsi > 70) return `Powerful trend but overbought conditions (RSI ${rsi.toFixed(0)}). Wait for a pullback to enter — chasing at this level risks a sharp reversal.`;
    if (adx > 25 && signal === 'bullish') return `Trending market (ADX ${adx.toFixed(0)}) supporting the bullish signal. RSI at ${rsi.toFixed(0)} — momentum is ${rsi > 50 ? 'positive' : 'building'}. Entry on pullback preferred.`;
    if (adx > 25 && signal === 'bearish') return `Trending market (ADX ${adx.toFixed(0)}) supporting the bearish signal. RSI at ${rsi.toFixed(0)} — ${rsi < 50 ? 'downside momentum in play' : 'watch for RSI confirmation below 50'}.`;
    if (adx < 20) return `Low trend strength (ADX ${adx.toFixed(0)}) — market is ranging. Reduce position size and avoid breakout strategies until ADX rises above 25.`;
    return `Developing trend (ADX ${adx.toFixed(0)}), RSI ${rsi.toFixed(0)}. Monitor for confirmation before committing full position size.`;
  }

  getTacticalContextLabel(): string {
    return this.analysis.strategy_mode === 'long_term' ? 'DAILY' : '1-HOUR';
  }

  getTacticalBiasClass(): 'bullish' | 'bearish' | 'neutral' {
    return this.analysis.daily_strength.signal;
  }

  getTacticalBiasText(): string {
    const signal = this.analysis.daily_strength.signal;
    const rsi = this.analysis.daily_strength.rsi;
    const trend = this.analysis.monthly_trend.direction;

    if (signal === 'bullish') return 'BULLISH MOMENTUM BIAS';
    if (signal === 'bearish') {
      if (trend === 'bullish' && rsi >= 70) return 'OVERBOUGHT PULLBACK RISK';
      return 'BEARISH MOMENTUM BIAS';
    }
    return 'NEUTRAL / WAIT FOR BREAK';
  }

  private extractStrengthReasons(limit: number = 2): string[] {
    const desc = this.analysis.daily_strength.description || '';
    const idx = desc.indexOf(':');
    if (idx < 0) return [];
    return desc
      .slice(idx + 1)
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
      .slice(0, limit);
  }

  getTacticalEvidence(): string[] {
    const a = this.analysis;
    const out: string[] = [];
    const adx = a.daily_strength.adx;
    const rsi = a.daily_strength.rsi;
    const vwapDist = a.daily_strength.vwap_dist_pct;

    out.push(`Trend regime: ADX ${adx.toFixed(1)} (${this.getADXInterpretation()}).`);

    if (rsi >= 70) out.push(`RSI ${rsi.toFixed(1)} is overbought — momentum can stay strong but pullback risk is elevated.`);
    else if (rsi <= 30) out.push(`RSI ${rsi.toFixed(1)} is oversold — downside may be exhausted, watch for reversal candles.`);
    else out.push(`RSI ${rsi.toFixed(1)} is in ${this.getRSIInterpretation().toLowerCase()} zone.`);

    if (vwapDist !== null && vwapDist !== undefined) {
      out.push(`Price vs VWAP: ${vwapDist >= 0 ? '+' : ''}${vwapDist.toFixed(2)}% (${this.getVWAPDistLabel().toLowerCase()}).`);
    }

    if (a.candle_patterns?.pattern && a.candle_patterns.pattern !== 'none') {
      out.push(`Execution candle: ${a.candle_patterns.pattern.replace(/_/g, ' ')} (${a.candle_patterns.is_bullish ? 'bullish' : 'bearish'}).`);
    }

    for (const reason of this.extractStrengthReasons(2)) {
      out.push(`Signal driver: ${reason}.`);
    }

    return out.slice(0, 5);
  }

  private formatPrice(v: number | null | undefined): string {
    return (v !== null && v !== undefined && Number.isFinite(v)) ? `$${v.toFixed(2)}` : 'N/A';
  }

  getBullTriggerText(): string {
    const up = this.analysis.trade_signal.signal_conflict?.trigger_price_up;
    const r1 = this.analysis.technical_indicators?.pivot_points?.r1;
    const trigger = up ?? r1 ?? this.analysis.current_price;
    return `Daily close above ${this.formatPrice(trigger)}`;
  }

  getBullTargetText(): string {
    const tp = this.analysis.volatility_risk?.take_profit;
    const r2 = this.analysis.technical_indicators?.pivot_points?.r2;
    return this.formatPrice(tp ?? r2 ?? null);
  }

  getBullInvalidationText(): string {
    const stop = this.analysis.volatility_risk?.stop_loss;
    const pivot = this.analysis.technical_indicators?.pivot_points?.pivot;
    return `Close below ${this.formatPrice(stop ?? pivot ?? null)}`;
  }

  getBearTriggerText(): string {
    const down = this.analysis.trade_signal.signal_conflict?.trigger_price_down;
    const s1 = this.analysis.technical_indicators?.pivot_points?.s1;
    const trigger = down ?? s1 ?? this.analysis.current_price;
    return `Daily close below ${this.formatPrice(trigger)}`;
  }

  getBearTargetText(): string {
    const s2 = this.analysis.technical_indicators?.pivot_points?.s2;
    const stop = this.analysis.volatility_risk?.stop_loss;
    return this.formatPrice(s2 ?? stop ?? null);
  }

  getBearInvalidationText(): string {
    const r1 = this.analysis.technical_indicators?.pivot_points?.r1;
    const tp = this.analysis.volatility_risk?.take_profit;
    return `Close above ${this.formatPrice(r1 ?? tp ?? null)}`;
  }

  getTacticalExecutionNote(): string {
    const rec = this.analysis.trade_signal.recommendation;
    if (rec === 'bullish') {
      return 'Execution plan: prioritize long continuation only after trigger confirmation; avoid fresh size if price is already stretched above VWAP.';
    }
    if (rec === 'bearish') {
      return 'Execution plan: prioritize short continuation only after breakdown confirmation; avoid early shorts into strong support without close confirmation.';
    }
    return 'Execution plan: market is in a conflict/neutral state — treat both scenarios as conditional and commit size only on confirmed close beyond trigger levels.';
  }

  getAnalysisAge(): string {
    if (!this.analysis.last_updated) return 'N/A';
    const updated = new Date(this.analysis.last_updated);
    const diffMs = Date.now() - updated.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ${diffMin % 60}m ago`;
    return updated.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  isPlanStale(): boolean {
    if (!this.analysis.last_updated) return false;
    const diffMin = Math.floor((Date.now() - new Date(this.analysis.last_updated).getTime()) / 60000);
    return diffMin > 30;
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

  getTrendCorrelation(): string {
    const dir = this.analysis.monthly_trend.direction;
    const isAbove = this.analysis.monthly_trend.price_above_slow_ma;
    if (dir === 'bullish') return isAbove ? 'Macro trend confirms strong institutional accumulation.' : 'Bullish intent but struggling below long-term MA.';
    if (dir === 'bearish') return !isAbove ? 'Bearish structure confirmed. Market is in heavy distribution.' : 'Bearish trend with potential relief rally above MA.';
    return 'Consolidation phase. Wait for macro structural breakout.';
  }

  getMomentumCorrelation(): string {
    const adx = this.analysis.daily_strength.adx;
    if (adx >= 35) return 'Ultra-Strong Trend: Momentum is locked - do not fight this move.';
    if (adx >= 25) return 'Established Momentum: Trend is healthy and gaining traction.';
    if (adx >= 15) return 'Weak Momentum: Price is ranging - expect chop and fakeouts.';
    return 'Dead State: Trendless market. Low probability area.';
  }

  getVolumeCorrelation(): string {
    const vol = this.analysis.daily_strength.volume_ratio;
    if (vol >= 2.0) return 'Institutional Spike: Heavy participation confirms the move.';
    if (vol >= 1.0) return 'Healthy Liquidity: Buying/Selling interest is professionally backed.';
    if (vol >= 0.5) return 'Retail Participation: Average volume - lacks big money intent.';
    return 'Trap Alert: Move is deceptive with zero institutional support.';
  }

  getRSICorrelation(): string {
    const rsi = this.analysis.daily_strength.rsi;
    if (rsi > 70) return 'Climax State: Price is overheated. High risk of mean-reversion.';
    if (rsi < 30) return 'Exhaustion State: Sellers are depleted. Potential reversal area.';
    return 'Room to Run: Neutral heat levels suggest further expansion room.';
  }

  getBetaCorrelation(): string {
    const beta = this.analysis.benchmark_direction;
    const rec = this.analysis.trade_signal.recommendation;
    if (beta === rec) return `Market Synergy: ${beta.toUpperCase()} benchmark is pulling this symbol with it.`;
    if (beta === 'neutral') return 'Market Independence: Decoupled from benchmark - symbol leads.';
    return 'Market Friction: Benchmark is fighting this direction. High risk.';
  }

  getRiskCorrelation(): string {
    const score = this.analysis.pullback_warning?.warning_score ?? 0;
    if (score >= 6) return 'Danger Zone: Multiple traps detected (Divergence, Over-extension).';
    if (score >= 3) return 'Moderate Friction: Some technical headwinds present. Reduce size.';
    return 'Clean Window: Low internal resistance. Path is structurally clear.';
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

  // ── Visual R/R Diagram Helpers ──────────────────────────────────────────────
  private isShortTrade(): boolean {
    return this.analysis.trade_signal?.recommendation?.toLowerCase() === 'bearish';
  }

  getRRReward(): string {
    const vr = this.analysis.volatility_risk;
    if (!vr) return '0.00';
    const entry = parseFloat(this.getEntryZone()) || (vr.stop_loss + vr.take_profit) / 2;
    const reward = this.isShortTrade()
      ? entry - vr.take_profit
      : vr.take_profit - entry;
    return Math.max(0, reward).toFixed(2);
  }

  getRRRisk(): string {
    const vr = this.analysis.volatility_risk;
    if (!vr) return '0.00';
    const entry = parseFloat(this.getEntryZone()) || (vr.stop_loss + vr.take_profit) / 2;
    const risk = this.isShortTrade()
      ? vr.stop_loss - entry
      : entry - vr.stop_loss;
    return Math.max(0, risk).toFixed(2);
  }

  getRRRatio(): string {
    const reward = parseFloat(this.getRRReward());
    const risk = parseFloat(this.getRRRisk());
    if (!risk) return '0.00';
    return (reward / risk).toFixed(2);
  }

  getExpectedValue(): string {
    const reward = parseFloat(this.getRRReward());
    const risk = parseFloat(this.getRRRisk());
    const winRate = (this.analysis.backtest_results?.win_rate || 50) / 100;
    return Math.max(0, reward * winRate - risk * (1 - winRate)).toFixed(2);
  }

  // ── AI Trade Reasoning ───────────────────────────────────────────────────────
  getTradeDirection(): string {
    return (this.analysis.trade_signal?.recommendation || 'neutral').toUpperCase();
  }

  getBullishFactors(): { indicator: string; value: string; explanation: string }[] {
    const factors: { indicator: string; value: string; explanation: string }[] = [];
    const a = this.analysis;

    if (a.monthly_trend?.direction === 'bullish') {
      factors.push({
        indicator: 'Monthly Trend',
        value: 'BULLISH',
        explanation: `Price above MA (${a.monthly_trend.fast_ma?.toFixed(2)} / ${a.monthly_trend.slow_ma?.toFixed(2)}). Long-term uptrend intact.`
      });
    }
    if (a.daily_strength?.signal === 'bullish') {
      factors.push({
        indicator: 'Daily Strength',
        value: `RSI ${a.daily_strength.rsi?.toFixed(0)} | ADX ${a.daily_strength.adx?.toFixed(0)}`,
        explanation: a.daily_strength.description || 'Daily momentum is bullish.'
      });
    }
    if (a.daily_strength?.adx > 25) {
      factors.push({
        indicator: 'Trend Strength (ADX)',
        value: `${a.daily_strength.adx?.toFixed(1)}`,
        explanation: a.daily_strength.adx > 40 ? 'Strong trend — momentum is strongly directional.' : 'Trending market — directional move in progress.'
      });
    }
    if (a.weekly_pullback?.detected && a.weekly_pullback?.near_support) {
      factors.push({
        indicator: 'Pullback to Support',
        value: `~\$${a.weekly_pullback.support_level?.toFixed(2)}`,
        explanation: `Price pulled back ${a.weekly_pullback.pullback_percent?.toFixed(1)}% and is near support — ideal entry zone.`
      });
    }
    if (a.relative_strength?.is_outperforming) {
      factors.push({
        indicator: 'Relative Strength',
        value: `Alpha +${a.relative_strength.alpha?.toFixed(2)}%`,
        explanation: `Outperforming benchmark by ${a.relative_strength.alpha?.toFixed(2)}%. ${a.relative_strength.label}`
      });
    }
    if (a.news_sentiment?.score && a.news_sentiment.score > 5) {
      factors.push({
        indicator: 'News Sentiment',
        value: `+${a.news_sentiment.score} (${a.news_sentiment.label})`,
        explanation: a.news_sentiment.sentiment_summary || 'Positive news flow supporting bullish bias.'
      });
    }
    if (a.candle_patterns?.is_bullish === true && a.candle_patterns.pattern !== 'none') {
      factors.push({
        indicator: 'Candle Pattern',
        value: a.candle_patterns.pattern,
        explanation: a.candle_patterns.description || 'Bullish candle pattern detected.'
      });
    }
    return factors;
  }

  getCautionFactors(): { indicator: string; value: string; explanation: string }[] {
    const factors: { indicator: string; value: string; explanation: string }[] = [];
    const a = this.analysis;

    if (a.monthly_trend?.direction === 'bearish') {
      factors.push({
        indicator: 'Monthly Trend',
        value: 'BEARISH',
        explanation: 'Long-term trend is down — trading against macro momentum.'
      });
    }
    if (a.monthly_trend?.direction === 'neutral') {
      factors.push({
        indicator: 'Monthly Trend',
        value: 'NEUTRAL',
        explanation: 'No clear long-term direction — trend-following edge reduced.'
      });
    }
    if (a.daily_strength?.rsi > 70) {
      factors.push({
        indicator: 'RSI Overbought',
        value: `RSI ${a.daily_strength.rsi?.toFixed(0)}`,
        explanation: 'Price may be extended. Wait for consolidation or pullback before entry.'
      });
    }
    if (a.daily_strength?.rsi < 30) {
      factors.push({
        indicator: 'RSI Oversold',
        value: `RSI ${a.daily_strength.rsi?.toFixed(0)}`,
        explanation: 'Selling pressure is intense. Confirm reversal signal before entering long.'
      });
    }
    if (a.pullback_warning?.is_warning) {
      factors.push({
        indicator: 'Pullback Warning',
        value: `Score ${a.pullback_warning.warning_score}`,
        explanation: a.pullback_warning.description || 'Trap or pullback risk detected.'
      });
    }
    if (a.fundamentals?.has_high_impact_events) {
      factors.push({
        indicator: 'High-Impact Events',
        value: '⚠ PENDING',
        explanation: `Economic events expected: ${a.fundamentals.events?.slice(0, 2).join(', ')}. Avoid large size.`
      });
    }
    if (a.news_sentiment?.score && a.news_sentiment.score < -5) {
      factors.push({
        indicator: 'News Sentiment',
        value: `${a.news_sentiment.score} (${a.news_sentiment.label})`,
        explanation: a.news_sentiment.sentiment_summary || 'Negative news flow — headwind for longs.'
      });
    }
    if (a.candle_patterns?.is_bullish === false && a.candle_patterns.pattern !== 'none') {
      factors.push({
        indicator: 'Candle Pattern',
        value: a.candle_patterns.pattern,
        explanation: a.candle_patterns.description || 'Bearish candle pattern — watch for reversal.'
      });
    }
    return factors;
  }

  getRangeUp(): string {
    const ti = this.analysis.technical_indicators;
    const price = this.analysis.current_price;
    if (ti?.pivot_points?.r1) {
      const r1 = ti.pivot_points.r1;
      const pct = (((r1 - price) / price) * 100).toFixed(1);
      return `R1 \$${r1?.toFixed(2)} (+${pct}%) → R2 \$${ti.pivot_points.r2?.toFixed(2)}`;
    }
    const tp = this.analysis.volatility_risk?.take_profit;
    return tp ? `Target \$${tp.toFixed(2)}` : 'See pivot levels above';
  }

  getRangeDown(): string {
    const ti = this.analysis.technical_indicators;
    const price = this.analysis.current_price;
    if (ti?.pivot_points?.s1) {
      const s1 = ti.pivot_points.s1;
      const pct = (((price - s1) / price) * 100).toFixed(1);
      return `S1 \$${s1?.toFixed(2)} (-${pct}%) → S2 \$${ti.pivot_points.s2?.toFixed(2)}`;
    }
    const sl = this.analysis.volatility_risk?.stop_loss;
    return sl ? `Stop \$${sl.toFixed(2)}` : 'See pivot levels above';
  }

  getReasoningDataLine(): string {
    const a = this.analysis;
    const parts: string[] = [];
    parts.push(`ADX=${a.daily_strength?.adx?.toFixed(0)}`);
    parts.push(`RSI=${a.daily_strength?.rsi?.toFixed(0)}`);
    parts.push(`Trend=${a.monthly_trend?.direction?.toUpperCase()}`);
    parts.push(`Phase=${a.market_phase?.phase?.toUpperCase()}`);
    if (a.daily_strength?.vwap_dist_pct != null) {
      parts.push(`VWAP=${a.daily_strength.vwap_dist_pct?.toFixed(2)}%`);
    }
    if (a.news_sentiment?.score != null) {
      parts.push(`News=${a.news_sentiment.score}`);
    }
    return parts.join(' | ');
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

