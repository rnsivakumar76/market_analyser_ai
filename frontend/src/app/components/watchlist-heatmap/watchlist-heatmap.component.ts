import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis, IntradaySignal } from '../../services/market-analyzer.service';

@Component({
    selector: 'app-watchlist-heatmap',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="heatmap-container">
      <div class="heatmap-header">
        <h3 class="heatmap-title">MARKET HEATMAP</h3>
        <div class="heatmap-legend">
          <span class="legend-item bullish">● Bullish</span>
          <span class="legend-item bearish">● Bearish</span>
          <span class="legend-item neutral">● Neutral</span>
        </div>
      </div>

      @if (getReadyInstruments().length > 0) {
      <div class="wl-group-header wl-ready">⚡ SETUP READY <span class="wl-group-count">{{ getReadyInstruments().length }}</span></div>
      <div class="heatmap-grid">
        @for (instrument of getReadyInstruments(); track instrument.symbol) {
          <div class="heat-cell"
               [class]="getCellClass(instrument)"
               [class.selected]="selectedSymbol === instrument.symbol"
               [class.trade-worthy]="instrument.trade_signal.trade_worthy"
               [title]="getCellTooltip(instrument)"
               (click)="select.emit(instrument)">
            <div class="cell-content">
              <span class="cell-symbol">{{ instrument.symbol }}</span>
              <span class="cell-score">{{ instrument.trade_signal.score > 0 ? '+' : '' }}{{ instrument.trade_signal.score }}</span>
              <span class="cell-change" [class]="getChangeClass(instrument)">
                {{ (instrument.daily_strength?.price_change_percent ?? 0) > 0 ? '+' : '' }}{{ (instrument.daily_strength?.price_change_percent ?? 0).toFixed(2) }}% · 1D
              </span>
              <span class="cell-phase">{{ instrument.market_phase?.phase || 'No Data' }}</span>
            </div>
            <div class="cell-gate-badge" [class]="'gates-' + getGateCount(instrument)">{{ getGateCount(instrument) }}/5</div>
            @if (instrument.trade_signal.trade_worthy) {
              <div class="worthy-glow"></div>
            }
            @if (instrument.pullback_warning?.is_warning) {
              <div class="cell-warning">⚠️</div>
            }
          </div>
        }
      </div>
      }

      <div class="wl-group-header wl-monitoring">👁 MONITORING <span class="wl-group-count">{{ getMonitoringInstruments().length }}</span></div>
      <div class="heatmap-grid">
        @for (instrument of getMonitoringInstruments(); track instrument.symbol) {
          <div class="heat-cell"
               [class]="getCellClass(instrument)"
               [class.selected]="selectedSymbol === instrument.symbol"
               [class.trade-worthy]="instrument.trade_signal.trade_worthy"
               [title]="getCellTooltip(instrument)"
               (click)="select.emit(instrument)">
            <div class="cell-content">
              <span class="cell-symbol">{{ instrument.symbol }}</span>
              <span class="cell-score">{{ instrument.trade_signal.score > 0 ? '+' : '' }}{{ instrument.trade_signal.score }}</span>
              <span class="cell-change" [class]="getChangeClass(instrument)">
                {{ (instrument.daily_strength?.price_change_percent ?? 0) > 0 ? '+' : '' }}{{ (instrument.daily_strength?.price_change_percent ?? 0).toFixed(2) }}% · 1D
              </span>
              <span class="cell-phase">{{ instrument.market_phase?.phase || 'No Data' }}</span>
            </div>
            <div class="cell-gate-badge" [class]="'gates-' + getGateCount(instrument)">{{ getGateCount(instrument) }}/5</div>
            @if (instrument.trade_signal.trade_worthy) {
              <div class="worthy-glow"></div>
            }
            @if (instrument.pullback_warning?.is_warning) {
              <div class="cell-warning">⚠️</div>
            }
          </div>
        }
      </div>

      <!-- LIVE SIGNALS FEED -->
      <div class="signals-section">
        <div class="signals-header">
          <span class="signals-title">⚡ LIVE SIGNALS</span>
          <span class="signals-count">{{ getActiveSignals().length }} active</span>
        </div>
        @if (signals && signals.length > 0) {
          @for (sig of getRecentSignals(); track sig.signal_id) {
          <div class="signal-row" [class]="'sig-' + sig.signal_type.toLowerCase()" [class.sig-expired]="sig.status === 'EXPIRED'">
            <div class="sig-left">
              <span class="sig-dir" [class]="sig.signal_type === 'LONG' ? 'sig-long' : 'sig-short'">{{ sig.signal_type === 'LONG' ? '▲' : '▼' }}</span>
              <div class="sig-meta">
                <span class="sig-sym">{{ sig.symbol }}</span>
                <span class="sig-tf">{{ sig.timeframe }}</span>
              </div>
            </div>
            <div class="sig-center">
              <span class="sig-trigger">{{ sig.trigger }}</span>
              <div class="sig-levels">
                <span class="sig-entry">E: {{ sig.entry_price }}</span>
                <span class="sig-sl bearish">SL: {{ sig.stop_loss }}</span>
                <span class="sig-tp bullish">TP1: {{ sig.take_profit_1 }}</span>
              </div>
            </div>
            <div class="sig-right">
              <div class="sig-conf" [class]="getConfClass(sig.confidence)">{{ sig.confidence }}%</div>
              <div class="sig-status" [class]="'status-' + sig.status.toLowerCase()">{{ sig.status }}</div>
            </div>
          </div>
          }
        } @else {
          <div class="signals-empty">No signals detected yet — scan runs every 15 min</div>
        }
      </div>
    </div>
  `,
    styles: [`
    .heatmap-container {
      padding: 16px;
      height: 100%;
      display: flex;
      flex-direction: column;
    }

    .heatmap-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding: 0 4px;
    }

    .heatmap-title {
      font-size: 0.90rem;
      font-weight: 800;
      letter-spacing: 1.5px;
      color: #64748b;
      margin: 0;
    }

    .heatmap-legend {
      display: flex;
      gap: 12px;
    }

    .legend-item {
      font-size: 0.86rem;
      font-weight: 600;
    }

    .legend-item.bullish { color: #86efac; }
    .legend-item.bearish { color: #f87171; }
    .legend-item.neutral { color: #fcd34d; }

    .heatmap-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 6px;
      flex: 1;
      align-content: flex-start;
    }

    @media (max-width: 600px) {
      .heatmap-grid {
        grid-template-columns: 1fr;
      }
    }

    .heat-cell {
      position: relative;
      min-height: 90px;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      border: 1px solid transparent;
    }

    .heat-cell:hover {
      transform: scale(1.03);
      z-index: 2;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }

    .heat-cell.selected {
      border-color: #60a5fa !important;
      box-shadow: 0 0 20px rgba(137, 180, 250, 0.25);
      transform: scale(1.04);
      z-index: 3;
    }

    /* Direction Colors */
    .heat-cell.bullish-cell {
      background: linear-gradient(145deg, rgba(166, 227, 161, 0.15), rgba(166, 227, 161, 0.08));
      border-color: rgba(166, 227, 161, 0.2);
    }

    .heat-cell.bearish-cell {
      background: linear-gradient(145deg, rgba(243, 139, 168, 0.15), rgba(243, 139, 168, 0.08));
      border-color: rgba(243, 139, 168, 0.2);
    }

    .heat-cell.neutral-cell {
      background: linear-gradient(145deg, rgba(249, 226, 175, 0.1), rgba(249, 226, 175, 0.05));
      border-color: rgba(249, 226, 175, 0.15);
    }

    /* Intensity via opacity scaling based on score */
    .heat-cell.high-conviction {
      &.bullish-cell {
        background: linear-gradient(145deg, rgba(166, 227, 161, 0.3), rgba(166, 227, 161, 0.15));
        border-color: rgba(166, 227, 161, 0.4);
      }
      &.bearish-cell {
        background: linear-gradient(145deg, rgba(243, 139, 168, 0.3), rgba(243, 139, 168, 0.15));
        border-color: rgba(243, 139, 168, 0.4);
      }
    }

    .cell-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      z-index: 1;
    }

    .cell-symbol {
      font-size: 0.95rem;
      font-weight: 800;
      color: #e2e8f0;
      letter-spacing: 0.5px;
    }

    .cell-score {
      font-size: 1.2rem;
      font-weight: 800;
      line-height: 1;
    }

    .bullish-cell .cell-score { color: #86efac; }
    .bearish-cell .cell-score { color: #f87171; }
    .neutral-cell .cell-score { color: #fcd34d; }

    .cell-change {
      font-size: 0.90rem;
      font-weight: 700;
    }

    .cell-change.positive { color: #86efac; }
    .cell-change.negative { color: #f87171; }
    .cell-change.neutral { color: #fcd34d; }

    .cell-phase {
      font-size: 0.76rem;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .worthy-glow {
      position: absolute;
      inset: 0;
      border-radius: 10px;
      box-shadow: inset 0 0 20px rgba(166, 227, 161, 0.1);
      animation: glow-pulse 3s ease-in-out infinite;
      pointer-events: none;
    }

    .cell-warning {
      position: absolute;
      top: 4px;
      right: 6px;
      font-size: 0.90rem;
    }

    .trade-worthy::after {
      content: '✓';
      position: absolute;
      top: 4px;
      left: 6px;
      font-size: 0.82rem;
      font-weight: 800;
      color: #86efac;
      background: rgba(166, 227, 161, 0.15);
      border-radius: 50%;
      width: 14px;
      height: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .wl-group-header {
      font-size: 0.72rem;
      font-weight: 900;
      letter-spacing: 1.2px;
      padding: 6px 4px 4px;
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 8px;
    }
    .wl-ready { color: #86efac; }
    .wl-monitoring { color: #334155; }
    .wl-group-count {
      background: rgba(108,112,134,0.15);
      color: #64748b;
      border-radius: 8px;
      padding: 1px 6px;
      font-size: 0.72rem;
    }

    .cell-gate-badge {
      position: absolute;
      bottom: 5px;
      right: 6px;
      font-size: 0.72rem;
      font-weight: 900;
      padding: 1px 5px;
      border-radius: 8px;
      letter-spacing: 0.3px;
    }
    .gates-5 { background: rgba(166,227,161,0.2); color: #86efac; border: 1px solid rgba(166,227,161,0.35); }
    .gates-4 { background: rgba(166,227,161,0.12); color: #86efac; border: 1px solid rgba(166,227,161,0.25); }
    .gates-3 { background: rgba(249,226,175,0.12); color: #fcd34d; border: 1px solid rgba(249,226,175,0.25); }
    .gates-2, .gates-1, .gates-0 { background: rgba(108,112,134,0.1); color: #334155; border: 1px solid rgba(108,112,134,0.2); }

    @keyframes glow-pulse {
      0%, 100% { opacity: 0.5; }
      50% { opacity: 1; }
    }

    /* LIVE SIGNALS FEED */
    .signals-section { margin-top: 16px; border-top: 1px solid #192642; padding-top: 12px; }
    .signals-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .signals-title { font-size: 0.72rem; font-weight: 900; letter-spacing: 1.2px; color: #60a5fa; }
    .signals-count { font-size: 0.72rem; color: #334155; background: rgba(96,165,250,0.1); padding: 1px 7px; border-radius: 8px; }
    .signal-row { display: flex; align-items: center; gap: 8px; padding: 7px 8px; border-radius: 6px; margin-bottom: 4px; border-left: 3px solid transparent; transition: opacity 0.2s; }
    .sig-long  { border-left-color: #86efac; background: rgba(134,239,172,0.05); }
    .sig-short { border-left-color: #f87171; background: rgba(248,113,113,0.05); }
    .sig-expired { opacity: 0.4; }
    .sig-left { display: flex; align-items: center; gap: 6px; width: 54px; flex-shrink: 0; }
    .sig-dir { font-size: 1.1rem; font-weight: 900; }
    .sig-long  .sig-dir { color: #86efac; }
    .sig-short .sig-dir { color: #f87171; }
    .sig-meta { display: flex; flex-direction: column; }
    .sig-sym { font-size: 0.80rem; font-weight: 900; color: #e2e8f0; }
    .sig-tf  { font-size: 0.68rem; color: #64748b; font-weight: 700; }
    .sig-center { flex: 1; display: flex; flex-direction: column; gap: 2px; }
    .sig-trigger { font-size: 0.68rem; color: #60a5fa; font-weight: 700; letter-spacing: 0.5px; }
    .sig-levels { display: flex; gap: 8px; flex-wrap: wrap; }
    .sig-entry, .sig-sl, .sig-tp { font-size: 0.70rem; font-weight: 700; }
    .sig-entry { color: #94a3b8; }
    .sig-sl { color: #f87171; }
    .sig-tp { color: #86efac; }
    .sig-right { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; width: 52px; flex-shrink: 0; }
    .sig-conf { font-size: 0.74rem; font-weight: 900; padding: 1px 6px; border-radius: 8px; }
    .conf-high   { background: rgba(134,239,172,0.15); color: #86efac; }
    .conf-medium { background: rgba(253,211,77,0.15);  color: #fcd34d; }
    .conf-low    { background: rgba(100,116,139,0.15); color: #64748b; }
    .sig-status  { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.5px; color: #475569; }
    .status-active   { color: #60a5fa; }
    .status-hit_tp1, .status-hit_tp2 { color: #86efac; }
    .status-hit_sl   { color: #f87171; }
    .status-expired  { color: #334155; }
    .signals-empty { font-size: 0.76rem; color: #334155; text-align: center; padding: 12px 0; }
  `]
})
export class WatchlistHeatmapComponent {
    @Input({ required: true }) instruments!: InstrumentAnalysis[];
    @Input() selectedSymbol: string | null = null;
    @Input() signals: IntradaySignal[] = [];
    @Output() select = new EventEmitter<InstrumentAnalysis>();

    getActiveSignals(): IntradaySignal[] {
        return (this.signals || []).filter(s => s.status === 'ACTIVE');
    }

    getRecentSignals(): IntradaySignal[] {
        return (this.signals || []).slice(0, 12);
    }

    getConfClass(confidence: number): string {
        if (confidence >= 75) return 'sig-conf conf-high';
        if (confidence >= 60) return 'sig-conf conf-medium';
        return 'sig-conf conf-low';
    }

    getGateCount(inst: InstrumentAnalysis): number {
        let count = 0;
        // Handle failed analyses where some fields might be null
        if (inst.monthly_trend && inst.trade_signal && inst.monthly_trend.direction === inst.trade_signal.recommendation) count++;
        if (inst.daily_strength && inst.daily_strength.adx >= 25) count++;
        if (inst.daily_strength && inst.daily_strength.volume_ratio >= 1.0) count++;
        if ((inst.pullback_warning?.warning_score ?? 0) <= 2) count++;
        if (!inst.trade_signal.signal_conflict?.conflict_type || inst.trade_signal.signal_conflict.conflict_type === 'none') count++;
        return count;
    }

    getReadyInstruments(): InstrumentAnalysis[] {
        return this.instruments.filter(i => this.getGateCount(i) >= 3);
    }

    getMonitoringInstruments(): InstrumentAnalysis[] {
        return this.instruments.filter(i => this.getGateCount(i) < 3);
    }

    getCellClass(instrument: InstrumentAnalysis): string {
        const direction = instrument.trade_signal.recommendation;
        const score = Math.abs(instrument.trade_signal.score);
        const dirClass = direction === 'bullish' ? 'bullish-cell' :
            direction === 'bearish' ? 'bearish-cell' : 'neutral-cell';
        const convictionClass = score >= 40 ? 'high-conviction' : '';
        return `${dirClass} ${convictionClass}`;
    }

    getCellWeight(instrument: InstrumentAnalysis): number {
        // Higher absolute score = bigger cell
        const score = Math.abs(instrument.trade_signal.score);
        return Math.max(1, Math.round(score / 15));
    }

    getChangeClass(instrument: InstrumentAnalysis): string {
        const change = instrument.daily_strength?.price_change_percent ?? 0;
        if (change > 0) return 'positive';
        if (change < 0) return 'negative';
        return 'neutral';
    }

    getCellTooltip(instrument: InstrumentAnalysis): string {
        const s = instrument.trade_signal;
        const priceChange = instrument.daily_strength?.price_change_percent ?? 0;
        const phase = instrument.market_phase?.phase || 'No Data';
        return `${instrument.name}\nScore: ${s.score} | ${s.recommendation.toUpperCase()}\n1D: ${priceChange > 0 ? '+' : ''}${priceChange.toFixed(2)}%\n${phase} -> $${instrument.current_price}`;
    }
}
