import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis } from '../../services/market-analyzer.service';

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
      <div class="heatmap-grid">
        @for (instrument of instruments; track instrument.symbol) {
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
                {{ instrument.daily_strength.price_change_percent > 0 ? '+' : '' }}{{ instrument.daily_strength.price_change_percent.toFixed(2) }}% · 1D
              </span>
              <span class="cell-phase">{{ instrument.market_phase.phase }}</span>
            </div>
            @if (instrument.trade_signal.trade_worthy) {
              <div class="worthy-glow"></div>
            }
            @if (instrument.pullback_warning?.is_warning) {
              <div class="cell-warning">⚠️</div>
            }
          </div>
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
      font-size: 0.7rem;
      font-weight: 800;
      letter-spacing: 1.5px;
      color: #6c7086;
      margin: 0;
    }

    .heatmap-legend {
      display: flex;
      gap: 12px;
    }

    .legend-item {
      font-size: 0.65rem;
      font-weight: 600;
    }

    .legend-item.bullish { color: #a6e3a1; }
    .legend-item.bearish { color: #f38ba8; }
    .legend-item.neutral { color: #f9e2af; }

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
      border-color: #89b4fa !important;
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
      color: #cdd6f4;
      letter-spacing: 0.5px;
    }

    .cell-score {
      font-size: 1.2rem;
      font-weight: 800;
      line-height: 1;
    }

    .bullish-cell .cell-score { color: #a6e3a1; }
    .bearish-cell .cell-score { color: #f38ba8; }
    .neutral-cell .cell-score { color: #f9e2af; }

    .cell-change {
      font-size: 0.7rem;
      font-weight: 700;
    }

    .cell-change.positive { color: #a6e3a1; }
    .cell-change.negative { color: #f38ba8; }
    .cell-change.neutral { color: #f9e2af; }

    .cell-phase {
      font-size: 0.55rem;
      font-weight: 700;
      color: #6c7086;
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
      font-size: 0.7rem;
    }

    .trade-worthy::after {
      content: '✓';
      position: absolute;
      top: 4px;
      left: 6px;
      font-size: 0.6rem;
      font-weight: 800;
      color: #a6e3a1;
      background: rgba(166, 227, 161, 0.15);
      border-radius: 50%;
      width: 14px;
      height: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    @keyframes glow-pulse {
      0%, 100% { opacity: 0.5; }
      50% { opacity: 1; }
    }
  `]
})
export class WatchlistHeatmapComponent {
    @Input({ required: true }) instruments!: InstrumentAnalysis[];
    @Input() selectedSymbol: string | null = null;
    @Output() select = new EventEmitter<InstrumentAnalysis>();

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
        const change = instrument.daily_strength.price_change_percent;
        if (change > 0) return 'positive';
        if (change < 0) return 'negative';
        return 'neutral';
    }

    getCellTooltip(instrument: InstrumentAnalysis): string {
        const s = instrument.trade_signal;
        return `${instrument.name}\nScore: ${s.score} | ${s.recommendation.toUpperCase()}\n1D: ${instrument.daily_strength.price_change_percent > 0 ? '+' : ''}${instrument.daily_strength.price_change_percent.toFixed(2)}%\n${instrument.market_phase.phase} → $${instrument.current_price}`;
    }
}
