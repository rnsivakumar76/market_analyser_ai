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
    <div class="mtf-vertical-container">
      @for (tf of timeframes; track tf.label) {
        <div class="mtf-node-vertical" [class]="getNodeClass(tf)">
          <div class="node-header">
            <span class="status-badge" [class]="tf.direction">{{ tf.direction.toUpperCase() }}</span>
            <span class="node-label">{{ tf.label }}</span>
          </div>
          <div class="node-body">
            <p class="node-subtitle">{{ tf.phase }} {{ tf.direction !== 'neutral' ? 'trend signals' : 'neutral' }}</p>
          </div>
          @if (tf.pullback) { <span class="pullback-indicator">↩ PULLBACK</span> }
        </div>
      }
    </div>
  `,
    styles: [`
    .mtf-vertical-container { display: flex; flex-direction: column; gap: 12px; }
    
    .mtf-node-vertical { 
      background: #121220; border: 1px solid #1f1f3a; border-radius: 8px; 
      padding: 12px; position: relative; overflow: hidden;
      transition: border-color 0.2s;
    }
    .mtf-node-vertical:hover { border-color: #31315a; }

    .node-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
    
    .status-badge { 
      font-size: 0.6rem; font-weight: 800; padding: 2px 6px; border-radius: 4px; 
      color: #11111b; min-width: 60px; text-align: center;
    }
    .status-badge.bullish { background: #a6e3a1; color: #11111b; }
    .status-badge.bearish { background: #f38ba8; color: #11111b; }
    .status-badge.neutral { background: #f9e2af; color: #11111b; }

    .node-label { font-size: 0.85rem; font-weight: 800; color: #cdd6f4; text-transform: uppercase; letter-spacing: 0.5px; }
    
    .node-body { padding-left: 0; }
    .node-subtitle { font-size: 0.75rem; color: #9399b2; margin: 0; line-height: 1.4; }

    .pullback-indicator { 
      position: absolute; top: 12px; right: 12px; font-size: 0.6rem; 
      font-weight: 800; color: #fab387; background: rgba(250, 179, 135, 0.1); 
      padding: 2px 6px; border-radius: 4px; 
    }

    /* Node side borders to match image theme */
    .mtf-node-vertical.bullish-node { border-left: 3px solid #a6e3a1; }
    .mtf-node-vertical.bearish-node { border-left: 3px solid #f38ba8; }
    .mtf-node-vertical.neutral-node { border-left: 3px solid #f9e2af; }
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
        direction: a.weekly_pullback.detected ? 'bullish' : (a.monthly_trend.direction === 'bullish' ? 'neutral' : a.monthly_trend.direction),
        score: 0,
        phase: a.weekly_pullback.detected ? 'Pullback' : 'Extended',
        pullback: a.weekly_pullback.detected,
        strength: a.weekly_pullback.detected ? 'bullish' : 'neutral'
      },
      {
        label: `TACTICAL MOMENTUM (${isLongTerm ? 'DAILY' : '1-HOUR'})`,
        direction: a.daily_strength.signal,
        score: 0,
        phase: a.candle_patterns.pattern !== 'none' ? a.candle_patterns.pattern : 'Execution',
        pullback: false,
        strength: a.daily_strength.signal
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
