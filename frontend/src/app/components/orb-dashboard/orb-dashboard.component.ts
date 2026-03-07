import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis } from '../../services/market-analyzer.service';

@Component({
  selector: 'app-orb-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="orb-panel">
      <div class="orb-header">
        <span class="orb-title">⏰ ORB MONITOR</span>
        <span class="orb-subtitle">Opening Range Breakout Alerts</span>
      </div>

      @if (orbInstruments().length === 0) {
        <div class="orb-empty">
          <span class="orb-empty-icon">📊</span>
          <p>ORB data available in <strong>Short-Term</strong> mode only</p>
        </div>
      } @else {
        <div class="orb-grid">
          @for (item of orbInstruments(); track item.symbol) {
            <div class="orb-card"
                 [class]="getCardClass(item)"
                 (click)="select.emit(item.analysis)">

              <!-- Top row: Symbol + Status -->
              <div class="orb-top-row">
                <div class="orb-left">
                  <span class="orb-sym">{{ item.symbol }}</span>
                  <span class="orb-price">\${{ item.analysis.current_price | number:'1.2-2' }}</span>
                </div>
                <div class="orb-right">
                  <span class="orb-status-label" [class]="getStatusClass(item.plan.or_broken)">
                    {{ getStatusText(item.plan.or_broken) }}
                    @if (item.plan.is_high_intent) { 🔥 }
                  </span>
                  <span class="orb-rvol" [class.rvol-hot]="item.plan.rvol >= 1.8">
                    RVOL {{ item.plan.rvol }}x
                  </span>
                  <span class="orb-age" [class.orb-age--stale]="isORBStale(item.analysis)">🕐 {{ getORBAge(item.analysis) }}</span>
                </div>
              </div>

              <!-- Bottom row: Plain-English battle text -->
              <p class="orb-battle-text">{{ getORBText(item) }}</p>

            </div>
          }
        </div>

        <!-- Summary Footer -->
        <div class="orb-footer">
          <div class="orb-stat bull-text">
            <strong>{{ bullCount() }}</strong>
            <span>BREAKOUT ↑</span>
          </div>
          <div class="orb-stat bear-text">
            <strong>{{ bearCount() }}</strong>
            <span>BREAKDOWN ↓</span>
          </div>
          <div class="orb-stat intent-text">
            <strong>{{ intentCount() }}</strong>
            <span>HIGH INTENT 🔥</span>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .orb-panel {
      background: var(--sidebar-bg, #11111b);
      padding: 12px 14px 10px;
    }

    /* Header */
    .orb-header {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-bottom: 10px;
    }
    .orb-title {
      font-size: 0.65rem;
      font-weight: 900;
      letter-spacing: 1.5px;
      color: #6c7086;
    }
    .orb-subtitle {
      font-size: 0.5rem;
      color: #45475a;
      font-weight: 600;
    }

    /* Empty state */
    .orb-empty {
      text-align: center;
      padding: 20px 10px;
    }
    .orb-empty-icon { font-size: 1.5rem; display: block; margin-bottom: 8px; }
    .orb-empty p { font-size: 0.7rem; color: #585b70; line-height: 1.4; margin: 0; }
    .orb-empty strong { color: #89b4fa; }

    /* Card grid — 1 column, matching heatmap aesthetic */
    .orb-grid {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .orb-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 10px;
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.18s ease;
    }
    .orb-card:hover { filter: brightness(1.1); }
    .orb-top-row { display: flex; align-items: center; justify-content: space-between; }
    .orb-battle-text { font-size: 0.65rem; color: #a6adc8; line-height: 1.5; margin: 0; padding-top: 4px; border-top: 1px solid rgba(255,255,255,0.05); }

    /* Heatmap-matched gradient backgrounds */
    .orb-card.card-bull {
      background: linear-gradient(145deg, rgba(166,227,161,0.15), rgba(166,227,161,0.08));
      border-color: rgba(166,227,161,0.25);
    }
    .orb-card.card-bear {
      background: linear-gradient(145deg, rgba(243,139,168,0.15), rgba(243,139,168,0.08));
      border-color: rgba(243,139,168,0.25);
    }
    .orb-card.card-neutral {
      background: linear-gradient(145deg, rgba(249,226,175,0.1), rgba(249,226,175,0.05));
      border-color: rgba(249,226,175,0.15);
    }
    .orb-card.card-wait {
      background: rgba(255,255,255,0.02);
      border-color: rgba(69,71,90,0.3);
    }
    .orb-card.high-intent {
      box-shadow: 0 0 12px rgba(250,179,135,0.15);
    }

    /* Left — symbol + price */
    .orb-left {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .orb-sym {
      font-size: 0.95rem;
      font-weight: 900;
      color: #cdd6f4;
      letter-spacing: 0.5px;
    }
    .orb-price {
      font-size: 0.6rem;
      color: #6c7086;
      font-weight: 600;
    }

    /* Right — status text + rvol */
    .orb-right {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
    }
    .orb-status-label {
      font-size: 0.6rem;
      font-weight: 950;
      letter-spacing: 1px;
      padding: 3px 8px;
      border-radius: 4px;
    }
    .status-bull {
      color: #a6e3a1;
      background: rgba(166,227,161,0.12);
      border: 1px solid rgba(166,227,161,0.3);
    }
    .status-bear {
      color: #f38ba8;
      background: rgba(243,139,168,0.12);
      border: 1px solid rgba(243,139,168,0.3);
    }
    .status-wait {
      color: #f9e2af;
      background: rgba(249,226,175,0.08);
      border: 1px solid rgba(249,226,175,0.2);
    }
    .orb-rvol {
      font-size: 0.5rem;
      font-weight: 700;
      color: #45475a;
      letter-spacing: 0.5px;
    }
    .orb-rvol.rvol-hot { color: #fab387; }
    .orb-age { font-size: 0.45rem; font-weight: 700; color: #45475a; letter-spacing: 0.3px; }
    .orb-age--stale { color: #f38ba8; }

    /* Footer */
    .orb-footer {
      display: flex;
      justify-content: space-around;
      margin-top: 10px;
      padding: 8px 0 2px;
      border-top: 1px solid var(--border-primary, #1f1f3a);
    }
    .orb-stat {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
    }
    .orb-stat strong {
      font-size: 1rem;
      font-weight: 900;
      line-height: 1;
    }
    .orb-stat span {
      font-size: 0.45rem;
      font-weight: 700;
      letter-spacing: 0.5px;
    }
    .bull-text { color: #a6e3a1; }
    .bear-text { color: #f38ba8; }
    .intent-text { color: #fab387; }
  `]
})
export class OrbDashboardComponent {
  @Input({ required: true }) instruments!: InstrumentAnalysis[];
  @Output() select = new EventEmitter<InstrumentAnalysis>();

  orbInstruments(): { symbol: string; plan: any; analysis: InstrumentAnalysis }[] {
    return this.instruments
      .filter(i => i.expert_trade_plan && i.expert_trade_plan.or_high > 0)
      .map(i => ({
        symbol: i.symbol,
        plan: i.expert_trade_plan!,
        analysis: i,
      }));
  }

  bullCount(): number {
    return this.orbInstruments().filter(i => i.plan.or_broken === 'bullish').length;
  }

  bearCount(): number {
    return this.orbInstruments().filter(i => i.plan.or_broken === 'bearish').length;
  }

  intentCount(): number {
    return this.orbInstruments().filter(i => i.plan.is_high_intent).length;
  }

  /** Background card class — uses trade_signal.recommendation to match heatmap color */
  getCardClass(item: { plan: any; analysis: InstrumentAnalysis }): string {
    const trend = item.analysis.trade_signal.recommendation;
    const intent = item.plan.is_high_intent ? ' high-intent' : '';
    if (trend === 'bullish') return 'orb-card card-bull' + intent;
    if (trend === 'bearish') return 'orb-card card-bear' + intent;
    if (trend === 'neutral') return 'orb-card card-neutral' + intent;
    return 'orb-card card-wait' + intent;
  }

  /** Status text label based on ORB breakout state */
  getStatusText(broken: string): string {
    if (broken === 'bullish') return '▲ BULL BREAKOUT';
    if (broken === 'bearish') return '▼ BEAR BREAKDOWN';
    return '— INSIDE RANGE';
  }

  getStatusClass(broken: string): string {
    if (broken === 'bullish') return 'orb-status-label status-bull';
    if (broken === 'bearish') return 'orb-status-label status-bear';
    return 'orb-status-label status-wait';
  }

  getORBAge(analysis: InstrumentAnalysis): string {
    if (!analysis.last_updated) return 'N/A';
    const diffMs = Date.now() - new Date(analysis.last_updated).getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ${diffMin % 60}m ago`;
    return new Date(analysis.last_updated).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  isORBStale(analysis: InstrumentAnalysis): boolean {
    if (!analysis.last_updated) return false;
    return (Date.now() - new Date(analysis.last_updated).getTime()) > 30 * 60000;
  }

  /** Generate plain-English ORB battle text for each instrument */
  getORBText(item: { symbol: string; plan: any; analysis: InstrumentAnalysis }): string {
    const { or_high, or_low, or_broken, rvol, is_high_intent } = item.plan;
    const price = item.analysis.current_price;
    const signal = item.analysis.trade_signal.recommendation;
    const hi = or_high?.toFixed(2);
    const lo = or_low?.toFixed(2);
    const rvolStr = rvol >= 1.8 ? ` RVOL ${rvol}x — institutions active.` : '';

    if (or_broken === 'bullish') {
      const targetNote = signal === 'bullish'
        ? ' Trend confirmed — target next resistance.'
        : ' Caution: ORB breakout against bearish signal. Wait for confirmation.';
      return `Price broke above OR High ($${hi}). Bullish bias active. OR Low ($${lo}) is now key support — stay long above it.${targetNote}${rvolStr}`;
    }

    if (or_broken === 'bearish') {
      const targetNote = signal === 'bearish'
        ? ' Trend confirmed — target next support level.'
        : ' Caution: ORB breakdown against bullish signal. Avoid longs until OR Low reclaimed.';
      return `Price broke below OR Low ($${lo}). Bearish bias active. OR High ($${hi}) is now resistance.${targetNote}${rvolStr}`;
    }

    const rangeWidth = or_high && or_low ? (((or_high - or_low) / or_low) * 100).toFixed(2) : null;
    const rangeNote = rangeWidth ? ` Range width: ${rangeWidth}%.` : '';
    return `Price inside opening range ($${lo} – $${hi}).${rangeNote} Wait for a clear breakout above OR High or breakdown below OR Low before taking a position.`;
  }
}
