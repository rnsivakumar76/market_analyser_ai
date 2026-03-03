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
        <div class="orb-title-row">
          <span class="orb-icon">⏰</span>
          <span class="orb-title">ORB MONITOR</span>
          <span class="orb-subtitle">Opening Range Breakout</span>
        </div>
        <div class="orb-legend">
          <span class="leg bull">▲ BULL</span>
          <span class="leg bear">▼ BEAR</span>
          <span class="leg none">— WAIT</span>
        </div>
      </div>

      @if (orbInstruments().length === 0) {
        <div class="orb-empty">
          <span class="orb-empty-icon">📊</span>
          <p>ORB data available in <strong>Short-Term</strong> mode only</p>
        </div>
      } @else {
        <div class="orb-list">
          @for (item of orbInstruments(); track item.symbol) {
            <div class="orb-row"
                 [class.orb-bull]="item.plan.or_broken === 'bullish'"
                 [class.orb-bear]="item.plan.or_broken === 'bearish'"
                 [class.orb-none]="item.plan.or_broken === 'none'"
                 [class.high-intent]="item.plan.is_high_intent"
                 (click)="select.emit(item.analysis)">

              <!-- Direction Badge -->
              <div class="orb-dir" [class]="getDirClass(item.plan.or_broken)">
                {{ getDirIcon(item.plan.or_broken) }}
              </div>

              <!-- Symbol & Name -->
              <div class="orb-sym-block">
                <span class="orb-sym">{{ item.symbol }}</span>
                <span class="orb-price">\${{ item.analysis.current_price | number:'1.2-2' }}</span>
              </div>

              <!-- OR Range -->
              <div class="orb-range-block">
                <div class="orb-range-row">
                  <span class="orb-range-lbl">H</span>
                  <span class="orb-range-val res">\${{ item.plan.or_high | number:'1.2-2' }}</span>
                </div>
                <div class="orb-range-row">
                  <span class="orb-range-lbl">L</span>
                  <span class="orb-range-val sup">\${{ item.plan.or_low | number:'1.2-2' }}</span>
                </div>
              </div>

              <!-- OR Range Width % -->
              <div class="orb-width-block">
                <span class="orb-width-val">{{ getORBWidth(item.plan) }}</span>
                <span class="orb-width-lbl">RANGE</span>
              </div>

              <!-- RVOL + Intent -->
              <div class="orb-rvol-block">
                <span class="orb-rvol-val" [class.hot]="item.plan.rvol >= 1.8">
                  {{ item.plan.rvol }}x
                </span>
                <span class="orb-rvol-lbl">RVOL</span>
                @if (item.plan.is_high_intent) {
                  <span class="orb-fire">🔥</span>
                }
              </div>

            </div>
          }
        </div>

        <!-- Summary Footer -->
        <div class="orb-footer">
          <div class="orb-stat">
            <strong class="bull-text">{{ bullCount() }}</strong>
            <span>Breakout ↑</span>
          </div>
          <div class="orb-stat">
            <strong class="bear-text">{{ bearCount() }}</strong>
            <span>Breakdown ↓</span>
          </div>
          <div class="orb-stat">
            <strong class="intent-text">{{ intentCount() }}</strong>
            <span>High Intent 🔥</span>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .orb-panel {
      border-top: 1px solid var(--border-primary, #1f1f3a);
      background: var(--sidebar-bg, #11111b);
      padding: 14px 16px 10px;
    }

    /* Header */
    .orb-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .orb-title-row {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .orb-icon { font-size: 0.8rem; }
    .orb-title {
      font-size: 0.65rem;
      font-weight: 900;
      letter-spacing: 1.5px;
      color: #6c7086;
    }
    .orb-subtitle {
      font-size: 0.55rem;
      color: #45475a;
      font-weight: 600;
    }
    .orb-legend {
      display: flex;
      gap: 8px;
    }
    .leg {
      font-size: 0.55rem;
      font-weight: 800;
    }
    .leg.bull { color: #a6e3a1; }
    .leg.bear { color: #f38ba8; }
    .leg.none { color: #45475a; }

    /* Empty state */
    .orb-empty {
      text-align: center;
      padding: 20px 10px;
      color: #45475a;
    }
    .orb-empty-icon { font-size: 1.5rem; display: block; margin-bottom: 8px; }
    .orb-empty p { font-size: 0.7rem; color: #585b70; line-height: 1.4; margin: 0; }
    .orb-empty strong { color: #89b4fa; }

    /* List */
    .orb-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    /* Row */
    .orb-row {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.18s ease;
      background: rgba(255,255,255,0.02);
    }
    .orb-row:hover {
      background: rgba(137, 180, 250, 0.05);
      border-color: rgba(137, 180, 250, 0.15);
    }
    .orb-bull {
      border-left: 3px solid rgba(166, 227, 161, 0.6) !important;
      background: rgba(166, 227, 161, 0.04) !important;
    }
    .orb-bear {
      border-left: 3px solid rgba(243, 139, 168, 0.6) !important;
      background: rgba(243, 139, 168, 0.04) !important;
    }
    .orb-none {
      border-left: 3px solid rgba(69, 71, 90, 0.4) !important;
    }
    .orb-row.high-intent {
      box-shadow: 0 0 10px rgba(250, 179, 135, 0.1);
    }

    /* Direction Badge */
    .orb-dir {
      width: 28px;
      height: 28px;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 900;
      flex-shrink: 0;
    }
    .dir-bull {
      background: rgba(166, 227, 161, 0.15);
      color: #a6e3a1;
      border: 1px solid rgba(166, 227, 161, 0.3);
    }
    .dir-bear {
      background: rgba(243, 139, 168, 0.15);
      color: #f38ba8;
      border: 1px solid rgba(243, 139, 168, 0.3);
    }
    .dir-none {
      background: rgba(69, 71, 90, 0.2);
      color: #45475a;
      border: 1px solid rgba(69, 71, 90, 0.3);
    }

    /* Symbol Block */
    .orb-sym-block {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 1px;
      min-width: 42px;
    }
    .orb-sym {
      font-size: 0.8rem;
      font-weight: 900;
      color: #cdd6f4;
    }
    .orb-price {
      font-size: 0.6rem;
      color: #6c7086;
      font-weight: 600;
    }

    /* Range Block */
    .orb-range-block {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .orb-range-row {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .orb-range-lbl {
      font-size: 0.5rem;
      font-weight: 900;
      color: #45475a;
      width: 8px;
    }
    .orb-range-val {
      font-size: 0.65rem;
      font-weight: 700;
    }
    .orb-range-val.res { color: #f38ba8; }
    .orb-range-val.sup { color: #a6e3a1; }

    /* Width Block */
    .orb-width-block {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1px;
      min-width: 36px;
    }
    .orb-width-val {
      font-size: 0.7rem;
      font-weight: 900;
      color: #89b4fa;
    }
    .orb-width-lbl {
      font-size: 0.45rem;
      font-weight: 700;
      color: #45475a;
      letter-spacing: 0.5px;
    }

    /* RVOL Block */
    .orb-rvol-block {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1px;
      min-width: 32px;
      position: relative;
    }
    .orb-rvol-val {
      font-size: 0.7rem;
      font-weight: 900;
      color: #6c7086;
    }
    .orb-rvol-val.hot { color: #fab387; }
    .orb-rvol-lbl {
      font-size: 0.45rem;
      font-weight: 700;
      color: #45475a;
      letter-spacing: 0.5px;
    }
    .orb-fire {
      font-size: 0.65rem;
      position: absolute;
      top: -4px;
      right: -6px;
    }

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
      font-size: 0.5rem;
      color: #45475a;
      font-weight: 700;
      text-transform: uppercase;
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

  getDirClass(broken: string): string {
    if (broken === 'bullish') return 'dir-bull';
    if (broken === 'bearish') return 'dir-bear';
    return 'dir-none';
  }

  getDirIcon(broken: string): string {
    if (broken === 'bullish') return '▲';
    if (broken === 'bearish') return '▼';
    return '—';
  }

  getORBWidth(plan: any): string {
    if (!plan.or_high || !plan.or_low || plan.or_low === 0) return 'N/A';
    const mid = (plan.or_high + plan.or_low) / 2;
    if (mid === 0) return 'N/A';
    const pct = ((plan.or_high - plan.or_low) / mid) * 100;
    return pct.toFixed(2) + '%';
  }
}
