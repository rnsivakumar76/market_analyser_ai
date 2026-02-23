import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis } from '../../services/market-analyzer.service';

@Component({
    selector: 'app-instrument-summary',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="summary-card" [class]="getCardClass()" (click)="select.emit()">
      <div class="summary-header">
        <div class="symbol-info">
          <span class="symbol">{{ analysis.symbol }}</span>
          <span class="price">\${{ analysis.current_price.toFixed(2) }}</span>
        </div>
        <div class="signal-info">
          <div class="signal-badge" [class]="getSignalClass()">
            {{ analysis.trade_signal.recommendation.toUpperCase() }}
          </div>
          <div class="score" [class]="getScoreClass()">
            {{ analysis.trade_signal.score }}
          </div>
        </div>
      </div>
      
      <div class="summary-body">
        <div class="phase-badge" [class]="getPhaseClass()">
          {{ analysis.market_phase.phase.toUpperCase() }}
        </div>
        <div class="change" [class]="getPriceChangeClass()">
          {{ analysis.daily_strength.price_change_percent > 0 ? '+' : '' }}{{ analysis.daily_strength.price_change_percent.toFixed(2) }}%
        </div>
      </div>

      @if (analysis.news_sentiment && analysis.news_sentiment.label !== 'Neutral') {
        <div class="summary-sentiment" [class]="analysis.news_sentiment.label.toLowerCase()" [title]="analysis.news_sentiment.sentiment_summary">
          <span class="dot">●</span> {{ analysis.news_sentiment.label }} news
        </div>
      }
      
      @if (analysis.trade_signal.trade_worthy) {
        <div class="worthy-indicator">✓</div>
      }
    </div>
  `,
    styles: [`
    .summary-card {
      background: #1e1e2e;
      border-radius: 8px;
      padding: 12px;
      border: 1px solid #313244;
      cursor: pointer;
      transition: all 0.2s ease;
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .summary-card:hover {
      background: #2a2a3d;
      border-color: #45475a;
      transform: translateY(-2px);
    }

    .summary-card.bullish { border-left: 3px solid #a6e3a1; }
    .summary-card.bearish { border-left: 3px solid #f38ba8; }
    .summary-card.neutral { border-left: 3px solid #f9e2af; }

    .summary-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .symbol-info {
      display: flex;
      flex-direction: column;
    }

    .symbol {
      font-size: 1.1rem;
      font-weight: 700;
      color: #cdd6f4;
    }

    .price {
      font-size: 0.85rem;
      color: #bac2de;
    }

    .signal-info {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
    }

    .signal-badge {
      font-size: 0.65rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .signal-badge.bullish { background: rgba(166, 227, 161, 0.1); color: #a6e3a1; }
    .signal-badge.bearish { background: rgba(243, 139, 168, 0.1); color: #f38ba8; }
    .signal-badge.neutral { background: rgba(249, 226, 175, 0.1); color: #f9e2af; }

    .score {
      font-size: 0.85rem;
      font-weight: 700;
    }

    .score.positive { color: #a6e3a1; }
    .score.negative { color: #f38ba8; }
    .score.neutral { color: #f9e2af; }

    .summary-body {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .phase-badge {
      font-size: 0.6rem;
      font-weight: 800;
      padding: 1px 5px;
      border-radius: 3px;
      text-transform: uppercase;
      opacity: 0.8;
    }

    .phase-badge.markup { background: rgba(166, 227, 161, 0.2); color: #a6e3a1; }
    .phase-badge.markdown { background: rgba(243, 139, 168, 0.2); color: #f38ba8; }
    .phase-badge.accumulation { background: rgba(203, 166, 247, 0.2); color: #cba6f7; }
    .phase-badge.distribution { background: rgba(250, 179, 135, 0.2); color: #fab387; }
    .phase-badge.liquidation { background: #f38ba8; color: #11111b; }
    .phase-badge.consolidation { background: rgba(137, 180, 250, 0.2); color: #89b4fa; }

    .change {
      font-size: 0.75rem;
      font-weight: 600;
    }

    .change.positive { color: #a6e3a1; }
    .change.negative { color: #f38ba8; }

    .worthy-indicator {
      position: absolute;
      top: -5px;
      right: -5px;
      background: #a6e3a1;
      color: #11111b;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 10px;
      font-weight: bold;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }

    .summary-sentiment {
      font-size: 0.65rem;
      font-weight: 600;
      margin-top: 4px;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .summary-sentiment .dot { font-size: 0.8rem; }
    .summary-sentiment.bullish { color: #a6e3a1; }
    .summary-sentiment.bearish { color: #f38ba8; }
  `]
})
export class InstrumentSummaryComponent {
    @Input({ required: true }) analysis!: InstrumentAnalysis;
    @Output() select = new EventEmitter<void>();

    getCardClass() {
        return this.analysis.trade_signal.recommendation;
    }

    getSignalClass() {
        return this.analysis.trade_signal.recommendation;
    }

    getScoreClass() {
        const score = this.analysis.trade_signal.score;
        if (score > 2) return 'positive';
        if (score < -2) return 'negative';
        return 'neutral';
    }

    getPhaseClass() {
        return this.analysis.market_phase.phase;
    }

    getPriceChangeClass() {
        return this.analysis.daily_strength.price_change_percent >= 0 ? 'positive' : 'negative';
    }
}
