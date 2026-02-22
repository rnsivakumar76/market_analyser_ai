import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WeeklyPerformance } from '../../services/market-analyzer.service';

@Component({
    selector: 'app-performance-banner',
    standalone: true,
    imports: [CommonModule],
    template: `
    @if (performance()) {
      <div class="performance-card" [class.positive]="performance()!.total_pnl_percent > 0">
        <div class="banner-content">
          <div class="main-stat">
            <span class="label">Weekly Strategy PnL</span>
            <span class="value">{{ performance()!.total_pnl_percent > 0 ? '+' : '' }}{{ performance()!.total_pnl_percent }}%</span>
          </div>
          
          <div class="stats-grid">
            <div class="stat-item">
              <span class="s-label">Total "Perfect" Setups</span>
              <span class="s-value">{{ performance()!.total_trades }}</span>
            </div>
            <div class="stat-item">
              <span class="s-label">Win Rate</span>
              <span class="s-value">{{ performance()!.win_rate }}%</span>
            </div>
            <div class="stat-item">
              <span class="s-label">Best: {{ performance()!.best_trade_symbol }}</span>
              <span class="s-value good">+{{ performance()!.best_trade_pnl }}%</span>
            </div>
            <div class="stat-item">
              <span class="s-label">Worst: {{ performance()!.worst_trade_symbol }}</span>
              <span class="s-value bad">{{ performance()!.worst_trade_pnl }}%</span>
            </div>
          </div>
          
          <div class="description">
            {{ performance()!.description }}
          </div>
        </div>
      </div>
    }
  `,
    styles: [`
    .performance-card {
      background: #1e1e2e;
      border: 1px solid #313244;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 24px;
      position: relative;
      overflow: hidden;
    }

    .performance-card::before {
      content: "";
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      background: #f38ba8;
    }

    .performance-card.positive::before {
      background: #a6e3a1;
    }

    .banner-content {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    @media (min-width: 1024px) {
      .banner-content {
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
      }
    }

    .main-stat {
      display: flex;
      flex-direction: column;
    }

    .main-stat .label {
      font-size: 0.8rem;
      color: #9399b2;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.5px;
    }

    .main-stat .value {
      font-size: 2.2rem;
      font-weight: 800;
      color: #f38ba8;
    }

    .positive .main-stat .value {
      color: #a6e3a1;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
      flex: 1;
      max-width: 600px;
      margin: 0 24px;
    }

    @media (min-width: 768px) {
      .stats-grid {
        grid-template-columns: repeat(4, 1fr);
      }
    }

    .stat-item {
      display: flex;
      flex-direction: column;
    }

    .s-label {
      font-size: 0.7rem;
      color: #6c7086;
    }

    .s-value {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 1.1rem;
    }

    .s-value.good { color: #a6e3a1; }
    .s-value.bad { color: #f38ba8; }

    .description {
      font-size: 0.9rem;
      color: #a6adc8;
      font-style: italic;
      border-left: 2px solid #45475a;
      padding-left: 12px;
      max-width: 300px;
    }
  `]
})
export class PerformanceBannerComponent {
    performance = input<WeeklyPerformance | null>(null);
}
