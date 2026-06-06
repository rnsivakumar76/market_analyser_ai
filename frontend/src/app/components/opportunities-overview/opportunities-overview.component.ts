import { Component, Input, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis, StrategyMode } from '../../services/market-analyzer.service';

type DirectionFilter = 'all' | 'long' | 'short' | 'range';

@Component({
  selector: 'app-opportunities-overview',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="ovw">
      <!-- Hero header -->
      <div class="ovw-hero">
        <div class="ovw-hero-text">
          <h2 class="ovw-title">Trade Opportunities</h2>
          <p class="ovw-sub">Top setups ranked by quality — tap any row for the full analysis.</p>
        </div>
        <div class="ovw-mode">
          <button class="ovw-mode-btn" [class.active]="strategyMode === 'short_term'"
                  (click)="modeChange.emit('short_term')">⏱️ Short-Term</button>
          <button class="ovw-mode-btn" [class.active]="strategyMode === 'long_term'"
                  (click)="modeChange.emit('long_term')">📅 Long-Term</button>
        </div>
      </div>

      <!-- Filter chips -->
      <div class="ovw-filters">
        <button class="ovw-chip" [class.active]="filter() === 'all'" (click)="filter.set('all')">
          All <span class="ovw-chip-n">{{ instruments.length }}</span>
        </button>
        <button class="ovw-chip long" [class.active]="filter() === 'long'" (click)="filter.set('long')">
          ▲ Long <span class="ovw-chip-n">{{ countFor('long') }}</span>
        </button>
        <button class="ovw-chip short" [class.active]="filter() === 'short'" (click)="filter.set('short')">
          ▼ Short <span class="ovw-chip-n">{{ countFor('short') }}</span>
        </button>
        <button class="ovw-chip range" [class.active]="filter() === 'range'" (click)="filter.set('range')">
          ◆ Range <span class="ovw-chip-n">{{ countFor('range') }}</span>
        </button>
      </div>

      <!-- Ranked list -->
      @if (filtered().length > 0) {
      <div class="ovw-list">
        @for (inst of filtered(); track inst.symbol) {
          <button class="ovw-row" [class]="'dir-' + direction(inst)" (click)="select.emit(inst)">
            <!-- Rank + grade -->
            <div class="ovw-grade" [class]="'grade-' + (inst.trade_signal.opportunity_grade || 'D').toLowerCase()">
              {{ inst.trade_signal.opportunity_grade || '—' }}
            </div>

            <!-- Symbol + price -->
            <div class="ovw-id">
              <span class="ovw-sym">{{ inst.symbol }}</span>
              <span class="ovw-price">\${{ inst.current_price | number:'1.2-2' }}
                <span class="ovw-chg" [class.up]="(inst.daily_strength?.price_change_percent ?? 0) >= 0"
                      [class.down]="(inst.daily_strength?.price_change_percent ?? 0) < 0">
                  {{ (inst.daily_strength?.price_change_percent ?? 0) >= 0 ? '+' : '' }}{{ (inst.daily_strength?.price_change_percent ?? 0) | number:'1.2-2' }}%
                </span>
              </span>
            </div>

            <!-- Direction tag -->
            <div class="ovw-tags">
              <span class="ovw-dir-tag" [class]="'dir-' + direction(inst)">{{ directionLabel(inst) }}</span>
              <span class="ovw-horizon">{{ strategyMode === 'short_term' ? 'Short-Term' : 'Long-Term' }}</span>
            </div>

            <!-- Headline / verdict -->
            <div class="ovw-verdict">
              <span class="ovw-verdict-head">{{ headline(inst) }}</span>
              @if (inst.trade_signal.trade_worthy) {
                <span class="ovw-worthy">⚡ Trade-worthy</span>
              }
            </div>

            <!-- Score + chevron -->
            <div class="ovw-meta">
              <span class="ovw-score" [class]="'dir-' + direction(inst)">{{ inst.trade_signal.score > 0 ? '+' : '' }}{{ inst.trade_signal.score }}</span>
              <span class="ovw-chevron">›</span>
            </div>
          </button>
        }
      </div>
      } @else {
      <div class="ovw-empty">
        <div class="ovw-empty-icon">🔍</div>
        <p>No {{ filter() === 'all' ? '' : filter() }} setups right now. Try another filter or refresh the analysis.</p>
      </div>
      }
    </div>
  `,
  styles: [`
    .ovw { padding: 18px 20px 40px; max-width: 1100px; margin: 0 auto; }

    /* Hero */
    .ovw-hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
    .ovw-title { font-size: 1.5rem; font-weight: 900; color: var(--text-primary, #cdd6f4); margin: 0; letter-spacing: 0.3px; }
    .ovw-sub { font-size: 0.8rem; color: var(--text-tertiary, #6c7086); margin: 4px 0 0; }
    .ovw-mode { display: flex; gap: 6px; background: var(--bg-tertiary, #1e1e2e); padding: 4px; border-radius: 10px; }
    .ovw-mode-btn { border: none; background: transparent; color: var(--text-secondary, #a6adc8); font-size: 0.75rem; font-weight: 700; padding: 7px 12px; border-radius: 7px; cursor: pointer; transition: all 0.15s ease; }
    .ovw-mode-btn.active { background: var(--accent-primary, #89b4fa); color: #11111b; }

    /* Filters */
    .ovw-filters { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
    .ovw-chip { display: inline-flex; align-items: center; gap: 7px; border: 1px solid var(--border-primary, #313244); background: var(--bg-secondary, #181825); color: var(--text-secondary, #a6adc8); font-size: 0.78rem; font-weight: 700; padding: 8px 14px; border-radius: 999px; cursor: pointer; transition: all 0.15s ease; }
    .ovw-chip:hover { filter: brightness(1.15); }
    .ovw-chip-n { font-size: 0.68rem; background: rgba(255,255,255,0.08); padding: 1px 7px; border-radius: 999px; }
    .ovw-chip.active { background: var(--text-primary, #cdd6f4); color: #11111b; border-color: transparent; }
    .ovw-chip.long.active { background: #a6e3a1; }
    .ovw-chip.short.active { background: #f38ba8; }
    .ovw-chip.range.active { background: #f9e2af; }

    /* List */
    .ovw-list { display: flex; flex-direction: column; gap: 8px; }
    .ovw-row {
      display: grid;
      grid-template-columns: 44px minmax(110px, 1.1fr) auto minmax(160px, 2fr) auto;
      align-items: center;
      gap: 14px;
      width: 100%;
      text-align: left;
      padding: 12px 16px;
      border-radius: 12px;
      border: 1px solid var(--border-primary, #313244);
      background: var(--bg-secondary, #181825);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .ovw-row:hover { transform: translateY(-1px); border-color: var(--accent-primary, #89b4fa); box-shadow: 0 4px 18px rgba(0,0,0,0.25); }
    .ovw-row.dir-long { border-left: 3px solid #a6e3a1; }
    .ovw-row.dir-short { border-left: 3px solid #f38ba8; }
    .ovw-row.dir-range { border-left: 3px solid #f9e2af; }

    /* Grade badge */
    .ovw-grade { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 9px; font-weight: 900; font-size: 1rem; color: #11111b; }
    .grade-a { background: #a6e3a1; }
    .grade-b { background: #89b4fa; }
    .grade-c { background: #f9e2af; }
    .grade-d { background: #6c7086; color: #cdd6f4; }

    /* Id */
    .ovw-id { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .ovw-sym { font-size: 1rem; font-weight: 900; color: var(--text-primary, #cdd6f4); letter-spacing: 0.4px; }
    .ovw-price { font-size: 0.72rem; color: var(--text-tertiary, #6c7086); font-weight: 600; }
    .ovw-chg { margin-left: 4px; font-weight: 800; }
    .ovw-chg.up { color: #a6e3a1; }
    .ovw-chg.down { color: #f38ba8; }

    /* Tags */
    .ovw-tags { display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }
    .ovw-dir-tag { font-size: 0.62rem; font-weight: 900; letter-spacing: 0.8px; padding: 3px 9px; border-radius: 5px; }
    .ovw-dir-tag.dir-long { color: #a6e3a1; background: rgba(166,227,161,0.14); }
    .ovw-dir-tag.dir-short { color: #f38ba8; background: rgba(243,139,168,0.14); }
    .ovw-dir-tag.dir-range { color: #f9e2af; background: rgba(249,226,175,0.12); }
    .ovw-horizon { font-size: 0.56rem; font-weight: 700; color: var(--text-tertiary, #6c7086); letter-spacing: 0.5px; }

    /* Verdict */
    .ovw-verdict { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
    .ovw-verdict-head { font-size: 0.78rem; font-weight: 600; color: var(--text-secondary, #a6adc8); line-height: 1.35; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .ovw-worthy { font-size: 0.58rem; font-weight: 800; color: #fab387; letter-spacing: 0.4px; }

    /* Meta */
    .ovw-meta { display: flex; align-items: center; gap: 12px; justify-self: end; }
    .ovw-score { font-size: 1.05rem; font-weight: 900; }
    .ovw-score.dir-long { color: #a6e3a1; }
    .ovw-score.dir-short { color: #f38ba8; }
    .ovw-score.dir-range { color: #f9e2af; }
    .ovw-chevron { font-size: 1.4rem; color: var(--text-tertiary, #6c7086); font-weight: 700; }

    /* Empty */
    .ovw-empty { text-align: center; padding: 60px 20px; color: var(--text-tertiary, #6c7086); }
    .ovw-empty-icon { font-size: 2.4rem; margin-bottom: 10px; }
    .ovw-empty p { font-size: 0.85rem; max-width: 340px; margin: 0 auto; line-height: 1.5; }

    @media (max-width: 760px) {
      .ovw-row { grid-template-columns: 38px 1fr auto; row-gap: 8px; }
      .ovw-tags { grid-column: 2 / 4; flex-direction: row; align-items: center; gap: 8px; }
      .ovw-verdict { grid-column: 1 / 4; }
      .ovw-meta { grid-column: 3; grid-row: 1; }
    }
  `]
})
export class OpportunitiesOverviewComponent {
  @Input({ required: true }) instruments: InstrumentAnalysis[] = [];
  @Input() strategyMode: StrategyMode = 'long_term';
  @Output() select = new EventEmitter<InstrumentAnalysis>();
  @Output() modeChange = new EventEmitter<StrategyMode>();

  filter = signal<DirectionFilter>('all');

  private gradeRank(grade?: string): number {
    switch (grade) {
      case 'A': return 0;
      case 'B': return 1;
      case 'C': return 2;
      default: return 3;
    }
  }

  direction(inst: InstrumentAnalysis): 'long' | 'short' | 'range' {
    const rec = inst.trade_signal.recommendation;
    if (rec === 'bullish') return 'long';
    if (rec === 'bearish') return 'short';
    return 'range';
  }

  directionLabel(inst: InstrumentAnalysis): string {
    const d = this.direction(inst);
    return d === 'long' ? '▲ LONG' : d === 'short' ? '▼ SHORT' : '◆ RANGE';
  }

  headline(inst: InstrumentAnalysis): string {
    const v = inst.trade_signal.trade_verdict;
    if (v?.headline) return v.headline;
    return inst.trade_signal.action_plan || inst.trade_signal.executive_summary || inst.market_phase?.phase || '—';
  }

  countFor(dir: DirectionFilter): number {
    if (dir === 'all') return this.instruments.length;
    return this.instruments.filter(i => this.direction(i) === dir).length;
  }

  filtered(): InstrumentAnalysis[] {
    const f = this.filter();
    const list = f === 'all'
      ? [...this.instruments]
      : this.instruments.filter(i => this.direction(i) === f);
    return list.sort((a, b) => {
      const g = this.gradeRank(a.trade_signal.opportunity_grade) - this.gradeRank(b.trade_signal.opportunity_grade);
      if (g !== 0) return g;
      return Math.abs(b.trade_signal.score) - Math.abs(a.trade_signal.score);
    });
  }
}
