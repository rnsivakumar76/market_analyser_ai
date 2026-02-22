import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis } from '../../services/market-analyzer.service';

@Component({
  selector: 'app-instrument-card',
  standalone: true,
  imports: [CommonModule],
  template: `
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
          </div>
          <span class="name">{{ analysis.name }}</span>
        </div>
        <div class="price-info">
          <span class="price">\${{ analysis.current_price.toFixed(2) }}</span>
          <span class="change" [class]="getPriceChangeClass()">
            {{ analysis.daily_strength.price_change_percent > 0 ? '+' : '' }}{{ analysis.daily_strength.price_change_percent.toFixed(2) }}%
          </span>
        </div>
      </div>

      <div class="trade-signal">
        <div class="signal-badge" [class]="getSignalClass()">
          <span class="signal-icon">{{ getSignalIcon() }}</span>
          <span class="signal-text">{{ analysis.trade_signal.recommendation.toUpperCase() }}</span>
        </div>
        <div class="score">
          <span class="score-label">Score:</span>
          <span class="score-value" [class]="getScoreClass()">{{ analysis.trade_signal.score }}</span>
        </div>
        @if (analysis.trade_signal.trade_worthy) {
          <span class="trade-worthy">✓ Trade Worthy</span>
        }
      </div>

      <div class="analysis-grid">
        <div class="analysis-item">
          <div class="analysis-header">
            <span class="indicator" [class]="getTrendClass()">●</span>
            <span class="label">Monthly Trend</span>
          </div>
          <p class="description">{{ analysis.monthly_trend.description }}</p>
        </div>

        <div class="analysis-item phase-item">
          <div class="analysis-header">
            <span class="phase-badge" [class]="getPhaseClass()">
              {{ analysis.market_phase.phase.toUpperCase() }}
            </span>
            <span class="label">Market Structure Phase</span>
          </div>
          <p class="description">{{ analysis.market_phase.description }}</p>
        </div>

        <div class="analysis-item">
          <div class="analysis-header">
            <span class="indicator" [class]="getPullbackClass()">●</span>
            <span class="label">Weekly Pullback</span>
          </div>
          <p class="description">{{ analysis.weekly_pullback.description }}</p>
        </div>

        <div class="analysis-item">
          <div class="analysis-header">
            <span class="indicator" [class]="getStrengthClass()">●</span>
            <span class="label">Daily Strength</span>
          </div>
          <p class="description">{{ analysis.daily_strength.description }}</p>
        </div>
      </div>
      
      @if (analysis.volatility_risk) {
        <div class="risk-section">
          <div class="risk-header">Risk & Volatility Management</div>
          <div class="risk-grid">
            <div class="risk-item">
              <span class="risk-label">ATR (14D)</span>
              <span class="risk-value">{{ analysis.volatility_risk.atr.toFixed(3) }}</span>
            </div>
            <div class="risk-item">
              <span class="risk-label">Stop Loss</span>
              <span class="risk-value sl">\${{ analysis.volatility_risk.stop_loss.toFixed(3) }}</span>
            </div>
            <div class="risk-item">
              <span class="risk-label">Take Profit</span>
              <span class="risk-value tp">\${{ analysis.volatility_risk.take_profit.toFixed(3) }}</span>
            </div>
            <div class="risk-item">
              <span class="risk-label">RR Ratio</span>
              <span class="risk-value">{{ analysis.volatility_risk.risk_reward_ratio.toFixed(2) }}</span>
            </div>
          </div>
          <p class="description risk-desc">{{ analysis.volatility_risk.description }}</p>
        </div>
      }

      @if (analysis.fundamentals) {
        <div class="fundamentals-section" [class.warning]="analysis.fundamentals.has_high_impact_events">
          <div class="fundamentals-header">Fundamental Context</div>
          <p class="description fund-desc">{{ analysis.fundamentals.description }}</p>
          @if (analysis.fundamentals.events.length > 0) {
            <ul class="fund-events">
              @for (event of analysis.fundamentals.events; track event) {
                <li>{{ event }}</li>
              }
            </ul>
          }
        </div>
      }

      @if (analysis.backtest_results) {
        <div class="backtest-section" [class.low-confidence]="analysis.backtest_results.win_rate < 45">
          <div class="backtest-header">Strategy Probability (1Y Backtest)</div>
          <div class="backtest-stats">
            <div class="backtest-stat">
              <span class="stat-label">Win Rate</span>
              <span class="stat-val" [class.good]="analysis.backtest_results.win_rate >= 50">
                {{ analysis.backtest_results.win_rate.toFixed(1) }}%
              </span>
            </div>
            <div class="backtest-stat">
              <span class="stat-label">Total Trades</span>
              <span class="stat-val">{{ analysis.backtest_results.total_trades }}</span>
            </div>
            <div class="backtest-stat">
              <span class="stat-label">Profit Factor</span>
              <span class="stat-val">{{ analysis.backtest_results.profit_factor }}</span>
            </div>
          </div>
          <p class="description backtest-desc">{{ analysis.backtest_results.description }}</p>
        </div>
      }

      @if (analysis.position_sizing) {
        <div class="sizing-section">
          <div class="sizing-header">Risk-Adjusted Sizing</div>
          <div class="sizing-grid">
            <div class="sizing-item main">
              <span class="sizing-label">Suggested Units</span>
              <span class="sizing-value highlight">{{ analysis.position_sizing.suggested_units }}</span>
            </div>
            <div class="sizing-item">
              <span class="sizing-label">Risk Amount</span>
              <span class="sizing-value">\${{ analysis.position_sizing.risk_amount }}</span>
            </div>
            <div class="sizing-item">
              <span class="sizing-label">Risk %</span>
              <span class="sizing-value">{{ analysis.position_sizing.final_risk_percent }}%</span>
            </div>
            <div class="sizing-item">
              <span class="sizing-label">Corr. Penalty</span>
              <span class="sizing-value" [class.warn]="analysis.position_sizing.correlation_penalty > 0">
                -{{ analysis.position_sizing.correlation_penalty }}%
              </span>
            </div>
          </div>
          <p class="description sizing-desc">{{ analysis.position_sizing.description }}</p>
        </div>
      }

      <div class="indicators">
        <div class="indicator-item">
          <span class="ind-label">RSI</span>
          <span class="ind-value">{{ analysis.daily_strength.rsi.toFixed(1) }}</span>
        </div>
        <div class="indicator-item" title="Average Directional Index - Trend Strength">
          <span class="ind-label">ADX</span>
          <span class="ind-value" [class.strong]="analysis.daily_strength.adx > 25" [class.weak]="analysis.daily_strength.adx < 20">
            {{ analysis.daily_strength.adx.toFixed(1) }}
          </span>
        </div>
        <div class="indicator-item">
          <span class="ind-label">Volume</span>
          <span class="ind-value">{{ analysis.daily_strength.volume_ratio.toFixed(2) }}x</span>
        </div>
        <div class="indicator-item">
          <span class="ind-label">20 MA</span>
          <span class="ind-value">\${{ analysis.monthly_trend.fast_ma.toFixed(2) }}</span>
        </div>
      </div>

      @if (analysis.candle_patterns && analysis.candle_patterns.pattern !== 'none') {
        <div class="candle-trigger" [class.bullish]="analysis.candle_patterns.is_bullish === true" [class.bearish]="analysis.candle_patterns.is_bullish === false">
          <span class="trigger-label">Trigger Candle:</span>
          <span class="trigger-value">{{ analysis.candle_patterns.pattern.replace('_', ' ').toUpperCase() }}</span>
          <p class="trigger-desc">{{ analysis.candle_patterns.description }}</p>
        </div>
      }

      @if (analysis.trade_signal.reasons.length > 0) {
        <div class="reasons">
          <h4>Analysis Summary</h4>
          <ul>
            @for (reason of analysis.trade_signal.reasons; track reason) {
              <li>{{ reason }}</li>
            }
          </ul>
        </div>
      }
    </div>
  `,
  styles: [`
    .card {
      background: #1e1e2e;
      border-radius: 12px;
      padding: 20px;
      border: 1px solid #313244;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .card:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
    }

    .card.bullish {
      border-left: 4px solid #a6e3a1;
    }

    .card.bearish {
      border-left: 4px solid #f38ba8;
    }

    .card.neutral {
      border-left: 4px solid #f9e2af;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }

    .symbol-info {
      display: flex;
      flex-direction: column;
    }

    .symbol-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px; /* Added margin for spacing with name */
    }

    .symbol {
      font-size: 1.5rem;
      font-weight: 700;
      color: #cdd6f4;
      margin: 0;
    }

    .beta-status {
      font-size: 0.65rem;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 700;
      text-transform: uppercase;
    }

    .beta-status.good {
      background: rgba(166, 227, 161, 0.1);
      color: #a6e3a1;
      border: 1px solid rgba(166, 227, 161, 0.2);
    }

    .beta-status.bad {
      background: rgba(243, 139, 168, 0.1);
      color: #f38ba8;
      border: 1px solid rgba(243, 139, 168, 0.2);
    }

    .name {
      font-size: 0.8rem; /* Changed from 0.85rem */
      color: #6c7086;
    }

    .price {
      font-size: 1.25rem;
      font-weight: 600;
      color: #cdd6f4;
    }

    .change {
      display: block;
      font-size: 0.9rem;
      text-align: right;
    }

    .change.positive { color: #a6e3a1; }
    .change.negative { color: #f38ba8; }

    .trade-signal {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 12px;
      background: #181825;
      border-radius: 8px;
      margin-bottom: 16px;
    }

    .signal-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 20px;
      font-weight: 600;
      font-size: 0.85rem;
    }

    .signal-badge.bullish {
      background: rgba(166, 227, 161, 0.2);
      color: #a6e3a1;
    }

    .signal-badge.bearish {
      background: rgba(243, 139, 168, 0.2);
      color: #f38ba8;
    }

    .signal-badge.neutral {
      background: rgba(249, 226, 175, 0.2);
      color: #f9e2af;
    }

    .signal-icon {
      font-size: 1rem;
    }

    .score {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .score-label {
      color: #6c7086;
      font-size: 0.85rem;
    }

    .score-value {
      font-weight: 700;
      font-size: 1.1rem;
    }

    .score-value.positive { color: #a6e3a1; }
    .score-value.negative { color: #f38ba8; }
    .score-value.neutral { color: #f9e2af; }

    .trade-worthy {
      margin-left: auto;
      color: #a6e3a1;
      font-weight: 600;
      font-size: 0.85rem;
    }

    .analysis-grid {
      display: flex;
      flex-direction: column;
      gap: 12px;
      margin-bottom: 16px;
    }

    .analysis-item {
      padding: 10px;
      background: #181825;
      border-radius: 6px;
    }

    .analysis-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }

    .indicator {
      font-size: 0.75rem;
    }

    .indicator.bullish { color: #a6e3a1; }
    .indicator.bearish { color: #f38ba8; }
    .indicator.neutral { color: #f9e2af; }

    .label {
      font-weight: 600;
      color: #cdd6f4;
      font-size: 0.9rem;
    }

    .description {
      color: #a6adc8;
      font-size: 0.8rem;
      margin: 0;
      line-height: 1.4;
    }

    .phase-badge {
      font-size: 0.65rem;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .phase-badge.markup { background: rgba(166, 227, 161, 0.2); color: #a6e3a1; border: 1px solid #a6e3a1; }
    .phase-badge.markdown { background: rgba(243, 139, 168, 0.2); color: #f38ba8; border: 1px solid #f38ba8; }
    .phase-badge.accumulation { background: rgba(203, 166, 247, 0.2); color: #cba6f7; border: 1px solid #cba6f7; }
    .phase-badge.distribution { background: rgba(250, 179, 135, 0.2); color: #fab387; border: 1px solid #fab387; }
    .phase-badge.liquidation { background: #f38ba8; color: #11111b; }
    .phase-badge.consolidation { background: rgba(137, 180, 250, 0.2); color: #89b4fa; border: 1px solid #89b4fa; }

    .phase-item {
      border: 1px solid rgba(205, 214, 244, 0.1);
      background: rgba(24, 24, 37, 0.5);
    }

    .risk-section {
      background: rgba(30, 30, 46, 0.6);
      border: 1px solid #313244;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .risk-header {
      color: #f9e2af;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .risk-header::before {
      content: "🛡️";
    }

    .risk-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 8px;
    }

    .risk-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .risk-label {
      font-size: 0.7rem;
      color: #6c7086;
    }

    .risk-value {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 0.9rem;
    }

    .risk-value.sl { color: #f38ba8; }
    .risk-value.tp { color: #a6e3a1; }

    .risk-desc {
      font-style: italic;
      color: #9399b2;
      border-top: 1px dashed #313244;
      padding-top: 8px;
      margin-top: 4px;
    }

    .fundamentals-section {
      background: rgba(30, 30, 46, 0.6);
      border: 1px solid #313244;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .fundamentals-section.warning {
      border: 1px solid #f9e2af;
      background: rgba(249, 226, 175, 0.05);
    }

    .fundamentals-header {
      color: #89b4fa;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .fundamentals-header::before {
      content: "🌐";
    }

    .fundamentals-section.warning .fundamentals-header {
      color: #f9e2af;
    }

    .fund-desc {
      font-size: 0.8rem;
      line-height: 1.4;
      margin-bottom: 8px !important;
    }

    .fund-events {
      margin: 0;
      padding-left: 18px;
      list-style-type: "⚠️";
    }

    .fund-events li {
      color: #f9e2af;
      font-size: 0.75rem;
      font-weight: 600;
      margin-bottom: 4px;
      padding-left: 6px;
    }

    .backtest-section {
      background: rgba(30, 30, 46, 0.4);
      border: 1px solid #313244;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .backtest-section.low-confidence {
      border-color: #f38ba8;
      background: rgba(243, 139, 168, 0.05);
    }

    .backtest-header {
      color: #cba6f7;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .backtest-header::before {
      content: "📈";
    }

    .backtest-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
      margin-bottom: 8px;
    }

    .backtest-stat {
      display: flex;
      flex-direction: column;
    }

    .stat-label {
      font-size: 0.7rem;
      color: #6c7086;
    }

    .stat-val {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 0.9rem;
    }

    .stat-val.good { color: #a6e3a1; }

    .backtest-desc {
      font-size: 0.75rem;
      color: #a6adc8;
      border-top: 1px solid #313244;
      padding-top: 8px;
      margin-top: 4px;
      line-height: 1.4;
    }

    .indicators {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 16px;
    }

    .indicator-item {
      text-align: center;
      padding: 8px;
      background: #181825;
      border-radius: 6px;
    }

    .ind-label {
      display: block;
      font-size: 0.7rem;
      color: #6c7086;
      margin-bottom: 2px;
    }

    .ind-value {
      font-weight: 700;
      color: #cdd6f4;
    }

    .sizing-section {
      background: rgba(250, 179, 135, 0.05);
      border: 1px solid rgba(250, 179, 135, 0.2);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 16px;
    }

    .sizing-header {
      color: #fab387;
      font-size: 0.85rem;
      font-weight: 700;
      text-transform: uppercase;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .sizing-header::before {
      content: "⚖️";
    }

    .sizing-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 8px;
    }

    .sizing-item {
      display: flex;
      flex-direction: column;
    }

    .sizing-label {
      font-size: 0.7rem;
      color: #9399b2;
    }

    .sizing-value {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 0.9rem;
    }

    .sizing-value.highlight {
      color: #fab387;
      font-size: 1.1rem;
    }

    .sizing-value.warn {
      color: #f38ba8;
    }

    .sizing-desc {
      font-size: 0.75rem;
      color: #a6adc8;
      border-top: 1px solid rgba(250, 179, 135, 0.1);
      padding-top: 8px;
      margin-top: 4px;
    }

    .ind-value.strong { color: #a6e3a1; }
    .ind-value.weak { color: #6c7086; }

    .candle-trigger {
      background: rgba(203, 166, 247, 0.05);
      border: 1px dashed #cba6f7;
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 16px;
    }

    .candle-trigger.bullish {
      border-color: #a6e3a1;
      background: rgba(166, 227, 161, 0.05);
    }

    .candle-trigger.bearish {
      border-color: #f38ba8;
      background: rgba(243, 139, 168, 0.05);
    }

    .trigger-label {
      font-size: 0.7rem;
      color: #9399b2;
      font-weight: 600;
    }

    .trigger-value {
      font-weight: 800;
      font-size: 0.85rem;
      margin-left: 6px;
      color: #cdd6f4;
    }

    .trigger-desc {
      font-size: 0.75rem;
      color: #a6adc8;
      margin: 4px 0 0 0;
    }

    .reasons {
      padding-top: 12px;
      border-top: 1px solid #313244;
    }

    .reasons h4 {
      color: #cdd6f4;
      font-size: 0.9rem;
      margin: 0 0 8px 0;
    }

    .reasons ul {
      margin: 0;
      padding-left: 20px;
    }

    .reasons li {
      color: #a6adc8;
      font-size: 0.8rem;
      margin-bottom: 4px;
    }
  `]
})
export class InstrumentCardComponent {
  @Input({ required: true }) analysis!: InstrumentAnalysis;

  getCardClass(): string {
    return this.analysis.trade_signal.recommendation;
  }

  getSignalClass(): string {
    return this.analysis.trade_signal.recommendation;
  }

  getSignalIcon(): string {
    switch (this.analysis.trade_signal.recommendation) {
      case 'bullish': return '↑';
      case 'bearish': return '↓';
      default: return '→';
    }
  }

  getPriceChangeClass(): string {
    return this.analysis.daily_strength.price_change_percent >= 0 ? 'positive' : 'negative';
  }

  getScoreClass(): string {
    if (this.analysis.trade_signal.score > 20) return 'positive';
    if (this.analysis.trade_signal.score < -20) return 'negative';
    return 'neutral';
  }

  getTrendClass(): string {
    return this.analysis.monthly_trend.direction;
  }

  getPullbackClass(): string {
    if (this.analysis.weekly_pullback.detected && this.analysis.weekly_pullback.near_support) {
      return 'bullish';
    }
    if (this.analysis.weekly_pullback.detected) {
      return 'neutral';
    }
    return 'neutral';
  }

  getStrengthClass(): string {
    return this.analysis.daily_strength.signal;
  }

  getPhaseClass(): string {
    return this.analysis.market_phase.phase;
  }
}
