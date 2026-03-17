import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis } from '../../services/market-analyzer.service';

interface TimeframeSignal {
  label: string;
  direction: string;
  score: number;
  phase: string;
  pullback: boolean;
  strength: string;
}

@Component({
  selector: 'app-multi-timeframe-overlay',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="mtf-container">
      <div class="mtf-header">
        <span class="mtf-title">MULTI-TIMEFRAME ALIGNMENT</span>
        <span class="alignment-badge" [class]="getAlignmentClass()">
          {{ getAlignmentLabel() }}
        </span>
      </div>
      <div class="timeframe-chain">
        @for (tf of timeframes; track tf.label) {
          <div class="tf-node" [class]="getNodeClass(tf)">
            <div class="tf-label">{{ tf.label }}</div>
            <div class="tf-direction-badge" [class]="tf.direction">
              {{ tf.direction.toUpperCase() }}
            </div>
            <div class="tf-details">
              <span class="tf-phase">{{ tf.phase }}</span>
              <span class="tf-strength" [class]="tf.strength">{{ tf.strength }}</span>
            </div>
            @if (tf.pullback) {
              <span class="tf-pullback-dot" title="Pullback detected">↩</span>
            }
          </div>
          @if (!$last) {
            <div class="tf-connector" [class]="getConnectorClass($index)">
              <div class="connector-line"></div>
              <div class="connector-arrow">→</div>
            </div>
          }
        }
      </div>
      <p class="mtf-description">{{ getDescription() }}</p>
    </div>
  `,
  styles: [`
    .mtf-container {
      background: #1e1e2e;
      border: 1px solid #313244;
      border-radius: 12px;
      padding: 16px;
    }

    .mtf-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .mtf-title {
      font-size: 0.65rem;
      font-weight: 800;
      letter-spacing: 1.5px;
      color: #6c7086;
    }

    .alignment-badge {
      font-size: 0.6rem;
      font-weight: 800;
      padding: 3px 10px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .alignment-badge.aligned {
      background: rgba(166, 227, 161, 0.15);
      color: #a6e3a1;
      border: 1px solid rgba(166, 227, 161, 0.3);
    }

    .alignment-badge.partial {
      background: rgba(249, 226, 175, 0.15);
      color: #f9e2af;
      border: 1px solid rgba(249, 226, 175, 0.3);
    }

    .alignment-badge.conflicting {
      background: rgba(243, 139, 168, 0.15);
      color: #f38ba8;
      border: 1px solid rgba(243, 139, 168, 0.3);
    }

    .timeframe-chain {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 0;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      padding-bottom: 8px;
    }

    .tf-node {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      padding: 10px 16px;
      border-radius: 10px;
      background: rgba(17, 17, 27, 0.5);
      border: 1px solid #313244;
      min-width: 85px;
      transition: all 0.2s;
      position: relative;
    }

    .tf-node.bullish-node {
      border-color: rgba(166, 227, 161, 0.25);
      background: rgba(166, 227, 161, 0.05);
    }

    .tf-node.bearish-node {
      border-color: rgba(243, 139, 168, 0.25);
      background: rgba(243, 139, 168, 0.05);
    }

    .tf-node.neutral-node {
      border-color: rgba(249, 226, 175, 0.2);
      background: rgba(249, 226, 175, 0.03);
    }

    .tf-label {
      font-size: 0.6rem;
      font-weight: 800;
      color: #6c7086;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    .tf-direction-badge {
      font-size: 0.65rem;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .tf-direction-badge.bullish {
      background: rgba(166, 227, 161, 0.2);
      color: #a6e3a1;
    }

    .tf-direction-badge.bearish {
      background: rgba(243, 139, 168, 0.2);
      color: #f38ba8;
    }

    .tf-direction-badge.neutral {
      background: rgba(249, 226, 175, 0.15);
      color: #f9e2af;
    }

    .tf-details {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1px;
    }

    .tf-phase {
      font-size: 0.55rem;
      font-weight: 700;
      color: #585b70;
      text-transform: uppercase;
    }

    .tf-strength {
      font-size: 0.55rem;
      font-weight: 700;
    }

    .tf-strength.bullish { color: #a6e3a1; }
    .tf-strength.bearish { color: #f38ba8; }
    .tf-strength.neutral { color: #6c7086; }

    .tf-pullback-dot {
      position: absolute;
      top: -6px;
      right: -4px;
      font-size: 0.75rem;
      background: rgba(250, 179, 135, 0.2);
      color: #fab387;
      border-radius: 50%;
      width: 18px;
      height: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .tf-connector {
      display: flex;
      align-items: center;
      gap: 2px;
    }

    .connector-line {
      width: 20px;
      height: 2px;
      background: #313244;
    }

    .connector-arrow {
      font-size: 0.8rem;
      color: #45475a;
    }

    .tf-connector.aligned .connector-line {
      background: #a6e3a1;
    }

    .tf-connector.aligned .connector-arrow {
      color: #a6e3a1;
    }

    .tf-connector.conflicting .connector-line {
      background: #f38ba8;
    }

    .tf-connector.conflicting .connector-arrow {
      color: #f38ba8;
    }

    .mtf-description {
      font-size: 0.75rem;
      color: #a6adc8;
      margin: 12px 0 0;
      font-style: italic;
      text-align: center;
    }

    @media (max-width: 768px) {
      .mtf-container {
        padding: 12px;
      }

      .mtf-header {
        margin-bottom: 10px;
      }

      .timeframe-chain {
        justify-content: flex-start;
        padding-bottom: 10px;
      }

      .tf-node {
        min-width: 70px;
        padding: 8px 10px;
      }

      .tf-label {
        font-size: 0.5rem;
        letter-spacing: 0.5px;
      }

      .tf-direction-badge {
        font-size: 0.58rem;
        padding: 2px 6px;
      }

      .connector-line {
        width: 12px;
      }

      .mtf-description {
        font-size: 0.68rem;
      }
    }

    @media (max-width: 480px) {
      .mtf-title {
        font-size: 0.55rem;
      }

      .alignment-badge {
        font-size: 0.5rem;
        padding: 2px 7px;
      }

      .tf-node {
        min-width: 62px;
        padding: 6px 8px;
      }
    }
  `]
})
export class MultiTimeframeOverlayComponent {
  @Input({ required: true }) analysis!: InstrumentAnalysis;

  get timeframes(): TimeframeSignal[] {
    const a = this.analysis;
    const isLongTerm = a.strategy_mode === 'long_term';

    return [
      {
        label: `PRIMARY TREND (${isLongTerm ? 'MONTHLY' : 'DAILY'})`,
        direction: a.monthly_trend.direction,
        score: a.trade_signal.score,
        phase: 'Institutional',
        pullback: false,
        strength: a.monthly_trend.direction
      },
      {
        label: 'STRUCTURE PHASE',
        direction: a.market_phase.phase === 'markup' ? 'bullish' : (a.market_phase.phase === 'markdown' || a.market_phase.phase === 'liquidation' ? 'bearish' : 'neutral'),
        score: a.market_phase.score,
        phase: a.market_phase.phase.toUpperCase(),
        pullback: false,
        strength: 'neutral'
      },
      {
        label: `INTERMEDIATE STATE (${isLongTerm ? 'WEEKLY' : '4-HOUR'})`,
        direction: a.weekly_pullback.detected ? 'neutral' : (a.monthly_trend.direction === 'bullish' ? 'neutral' : a.monthly_trend.direction),
        score: 0,
        phase: a.weekly_pullback.detected ? 'Pullback' : 'Extended',
        pullback: a.weekly_pullback.detected,
        strength: a.weekly_pullback.detected ? 'neutral' : 'neutral'
      },
      {
        label: `TACTICAL MOMENTUM (${isLongTerm ? 'DAILY' : '1-HOUR'})`,
        direction: (['bullish', 'bearish', 'neutral'].includes(a.daily_strength.signal) ? a.daily_strength.signal : 'neutral'),
        score: 0,
        phase: (a.candle_patterns.pattern && a.candle_patterns.pattern !== 'none') ? a.candle_patterns.pattern.replace(/_/g, ' ') : 'Execution',
        pullback: false,
        strength: (['bullish', 'bearish', 'neutral'].includes(a.daily_strength.signal) ? a.daily_strength.signal : 'neutral')
      }
    ];
  }

  getNodeClass(tf: TimeframeSignal): string {
    if (tf.direction === 'bullish') return 'bullish-node';
    if (tf.direction === 'bearish') return 'bearish-node';
    return 'neutral-node';
  }

  getConnectorClass(index: number): string {
    const tfs = this.timeframes;
    if (index + 1 >= tfs.length) return '';
    const current = tfs[index].direction;
    const next = tfs[index + 1].direction;
    if (current === next) return 'aligned';
    if ((current === 'bullish' && next === 'bearish') || (current === 'bearish' && next === 'bullish')) return 'conflicting';
    return '';
  }

  getAlignmentClass(): string {
    const tfs = this.timeframes;
    const directions = tfs.map(t => t.direction);
    const allSame = directions.every(d => d === directions[0]);
    if (allSame) return 'aligned';
    const hasConflict = directions.includes('bullish') && directions.includes('bearish');
    return hasConflict ? 'conflicting' : 'partial';
  }

  getAlignmentLabel(): string {
    const cls = this.getAlignmentClass();
    if (cls === 'aligned') return '✓ Fully Aligned';
    if (cls === 'conflicting') return '✗ Conflicting';
    return '~ Partial';
  }

  getDescription(): string {
    const cls = this.getAlignmentClass();
    const tfs = this.timeframes;
    if (cls === 'aligned') {
      return `All timeframes agree on ${tfs[0].direction} — high-confidence directional environment.`;
    }
    if (cls === 'conflicting') {
      return 'Macro and micro timeframes are in conflict — avoid aggressive positioning until alignment improves.';
    }
    return 'Timeframes show partial alignment — exercise selectivity and manage position size carefully.';
  }
}
