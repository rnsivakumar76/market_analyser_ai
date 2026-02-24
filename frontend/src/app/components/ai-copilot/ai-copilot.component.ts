import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { InstrumentAnalysis, WeeklyPerformance, CorrelationData } from '../../services/market-analyzer.service';

@Component({
    selector: 'app-ai-copilot',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="copilot-bar" [class.expanded]="expanded">
      <div class="copilot-header" (click)="expanded = !expanded">
        <div class="copilot-label">
          <span class="copilot-icon">🤖</span>
          <span class="copilot-title">AI MORNING BRIEF</span>
          <span class="copilot-badge">COPILOT</span>
        </div>
        <span class="expand-icon">{{ expanded ? '▼' : '▲' }}</span>
      </div>
      @if (expanded) {
        <div class="copilot-body">
          <p class="brief-text">{{ briefText }}</p>
          <div class="brief-tags">
            @for (tag of tags; track tag.label) {
              <span class="tag" [class]="tag.type">{{ tag.label }}</span>
            }
          </div>
        </div>
      }
    </div>
  `,
    styles: [`
    .copilot-bar {
      background: linear-gradient(135deg, rgba(203, 166, 247, 0.08), rgba(137, 180, 250, 0.05));
      border: 1px solid rgba(203, 166, 247, 0.15);
      border-radius: 12px;
      margin: 12px 24px;
      overflow: hidden;
      transition: all 0.3s ease;
    }

    .copilot-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 16px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .copilot-header:hover {
      background: rgba(203, 166, 247, 0.05);
    }

    .copilot-label {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .copilot-icon {
      font-size: 1.1rem;
    }

    .copilot-title {
      font-size: 0.7rem;
      font-weight: 800;
      letter-spacing: 1.5px;
      color: #cba6f7;
    }

    .copilot-badge {
      font-size: 0.55rem;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 4px;
      background: linear-gradient(135deg, #cba6f7, #89b4fa);
      color: #11111b;
      letter-spacing: 0.5px;
    }

    .expand-icon {
      font-size: 0.75rem;
      color: #6c7086;
      transition: transform 0.3s;
    }

    .copilot-body {
      padding: 0 16px 14px;
      animation: fade-in-brief 0.3s ease;
    }

    .brief-text {
      font-size: 0.88rem;
      line-height: 1.7;
      color: #cdd6f4;
      margin: 0 0 12px;
      border-left: 3px solid #cba6f7;
      padding-left: 14px;
    }

    .brief-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .tag {
      font-size: 0.6rem;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .tag.bullish {
      background: rgba(166, 227, 161, 0.15);
      color: #a6e3a1;
      border: 1px solid rgba(166, 227, 161, 0.3);
    }

    .tag.bearish {
      background: rgba(243, 139, 168, 0.15);
      color: #f38ba8;
      border: 1px solid rgba(243, 139, 168, 0.3);
    }

    .tag.neutral {
      background: rgba(249, 226, 175, 0.15);
      color: #f9e2af;
      border: 1px solid rgba(249, 226, 175, 0.3);
    }

    .tag.info {
      background: rgba(137, 180, 250, 0.15);
      color: #89b4fa;
      border: 1px solid rgba(137, 180, 250, 0.3);
    }

    .tag.warning {
      background: rgba(250, 179, 135, 0.15);
      color: #fab387;
      border: 1px solid rgba(250, 179, 135, 0.3);
    }

    @keyframes fade-in-brief {
      from { opacity: 0; transform: translateY(-8px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `]
})
export class AiCopilotComponent implements OnChanges {
    @Input({ required: true }) instruments!: InstrumentAnalysis[];
    @Input() performance: WeeklyPerformance | null = null;
    @Input() correlationData: CorrelationData | null = null;

    expanded = true;
    briefText = '';
    tags: { label: string; type: string }[] = [];

    ngOnChanges(changes: SimpleChanges) {
        if (changes['instruments'] || changes['performance']) {
            this.generateBrief();
        }
    }

    private generateBrief() {
        if (!this.instruments || this.instruments.length === 0) return;

        const bullish = this.instruments.filter(i => i.trade_signal.recommendation === 'bullish');
        const bearish = this.instruments.filter(i => i.trade_signal.recommendation === 'bearish');
        const tradeWorthy = this.instruments.filter(i => i.trade_signal.trade_worthy);
        const pullbackWarnings = this.instruments.filter(i => i.pullback_warning?.is_warning);

        // Find strongest setup
        const sorted = [...this.instruments].sort((a, b) =>
            Math.abs(b.trade_signal.score) - Math.abs(a.trade_signal.score)
        );
        const strongest = sorted[0];

        // Determine overall market tone
        let marketTone: string;
        if (bullish.length > bearish.length * 2) {
            marketTone = 'risk-on';
        } else if (bearish.length > bullish.length * 2) {
            marketTone = 'risk-off';
        } else if (bullish.length > bearish.length) {
            marketTone = 'cautiously bullish';
        } else if (bearish.length > bullish.length) {
            marketTone = 'cautiously bearish';
        } else {
            marketTone = 'mixed / rotational';
        }

        // Build the brief
        const parts: string[] = [];

        parts.push(`Cross-asset sentiment is ${marketTone} with ${bullish.length} bullish vs ${bearish.length} bearish signals across your ${this.instruments.length}-instrument watchlist.`);

        if (strongest) {
            const dir = strongest.trade_signal.recommendation;
            parts.push(`The strongest conviction is ${strongest.symbol} (${dir}, score ${strongest.trade_signal.score > 0 ? '+' : ''}${strongest.trade_signal.score}) in a ${strongest.market_phase.phase} phase.`);
        }

        if (tradeWorthy.length > 0) {
            const symbols = tradeWorthy.map(t => t.symbol).join(', ');
            parts.push(`${tradeWorthy.length} setup${tradeWorthy.length > 1 ? 's' : ''} meet conviction threshold: ${symbols}.`);
        } else {
            parts.push('No setups currently meet your conviction threshold — patience is the edge.');
        }

        if (pullbackWarnings.length > 0) {
            const warnSymbols = pullbackWarnings.map(p => p.symbol).join(', ');
            parts.push(`⚠️ Pullback risk detected in ${warnSymbols}. Consider tightening stops or reducing exposure.`);
        }

        if (this.performance) {
            if (this.performance.total_trades > 0) {
                parts.push(`Weekly theoretical performance: ${this.performance.total_pnl_percent > 0 ? '+' : ''}${this.performance.total_pnl_percent}% across ${this.performance.total_trades} setups (${this.performance.win_rate}% win rate).`);
            }
        }

        this.briefText = parts.join(' ');

        // Generate tags
        this.tags = [];
        this.tags.push({
            label: `Market: ${marketTone}`,
            type: marketTone.includes('bullish') || marketTone === 'risk-on' ? 'bullish' :
                marketTone.includes('bearish') || marketTone === 'risk-off' ? 'bearish' : 'neutral'
        });

        if (tradeWorthy.length > 0) {
            this.tags.push({ label: `${tradeWorthy.length} Trade-Worthy`, type: 'bullish' });
        }

        if (pullbackWarnings.length > 0) {
            this.tags.push({ label: `${pullbackWarnings.length} Pullback Warning${pullbackWarnings.length > 1 ? 's' : ''}`, type: 'warning' });
        }

        // Per-instrument quick tags for strongest setups
        sorted.slice(0, 3).forEach(i => {
            const dir = i.trade_signal.recommendation;
            this.tags.push({
                label: `${i.symbol} ${i.trade_signal.score > 0 ? '+' : ''}${i.trade_signal.score}`,
                type: dir === 'bullish' ? 'bullish' : dir === 'bearish' ? 'bearish' : 'neutral'
            });
        });
    }
}
