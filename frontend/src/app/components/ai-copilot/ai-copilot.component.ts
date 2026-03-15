import { Component, Input, OnChanges, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CorrelationData,
    InstrumentAnalysis,
    MarketAnalyzerService,
    StrategyMode,
    WeeklyPerformance,
} from '../../services/market-analyzer.service';

@Component({
    selector: 'app-ai-copilot',
    standalone: true,
    imports: [CommonModule, FormsModule],
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

          <div class="chat-panel">
            <div class="chat-panel-header">Ask Copilot</div>
            <div class="quick-actions">
              <button type="button" class="quick-btn" (click)="askPreset('Why is this setup trade-worthy now?')">Why now?</button>
              <button type="button" class="quick-btn" (click)="askPreset('What is the key risk and invalidation level?')">Main risk</button>
              <button type="button" class="quick-btn" (click)="askPreset('What confirms the bigger move?')">Big move trigger</button>
            </div>

            <div class="chat-log">
              @for (msg of chatMessages; track $index) {
                <div class="chat-msg" [class.user]="msg.role === 'user'" [class.assistant]="msg.role === 'assistant'">
                  <span class="chat-role">{{ msg.role === 'user' ? 'YOU' : 'COPILOT' }}</span>
                  <span>{{ msg.content }}</span>
                </div>
              }
              @if (chatLoading) {
                <div class="chat-msg assistant"><span class="chat-role">COPILOT</span><span>Thinking...</span></div>
              }
            </div>

            <div class="chat-compose">
              <textarea
                [(ngModel)]="chatDraft"
                rows="2"
                maxlength="600"
                placeholder="Ask about setup quality, risk, or trigger confirmation..."
              ></textarea>
              <button type="button" class="send-btn" (click)="sendChat()" [disabled]="chatLoading || !chatDraft.trim()">Send</button>
            </div>
            @if (chatError) {
              <div class="chat-error">{{ chatError }}</div>
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

    .chat-panel {
      margin-top: 14px;
      border-top: 1px solid rgba(137, 180, 250, 0.2);
      padding-top: 12px;
    }

    .chat-panel-header {
      font-size: 0.66rem;
      letter-spacing: 1.1px;
      font-weight: 800;
      color: #89b4fa;
      margin-bottom: 8px;
      text-transform: uppercase;
    }

    .quick-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }

    .quick-btn {
      border: 1px solid rgba(203, 166, 247, 0.35);
      background: rgba(30, 30, 46, 0.7);
      color: #cdd6f4;
      font-size: 0.66rem;
      padding: 4px 8px;
      border-radius: 7px;
      cursor: pointer;
    }

    .quick-btn:hover {
      background: rgba(203, 166, 247, 0.16);
    }

    .chat-log {
      max-height: 190px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 10px;
      padding-right: 4px;
    }

    .chat-msg {
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 0.74rem;
      line-height: 1.45;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .chat-msg.user {
      background: rgba(137, 180, 250, 0.12);
      border: 1px solid rgba(137, 180, 250, 0.35);
      color: #cdd6f4;
    }

    .chat-msg.assistant {
      background: rgba(166, 227, 161, 0.08);
      border: 1px solid rgba(166, 227, 161, 0.25);
      color: #cdd6f4;
    }

    .chat-role {
      font-size: 0.55rem;
      font-weight: 800;
      letter-spacing: 0.7px;
      opacity: 0.75;
    }

    .chat-compose {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: end;
    }

    .chat-compose textarea {
      width: 100%;
      resize: vertical;
      min-height: 48px;
      border-radius: 8px;
      border: 1px solid rgba(137, 180, 250, 0.3);
      background: rgba(17, 17, 27, 0.8);
      color: #cdd6f4;
      padding: 8px;
      font-size: 0.73rem;
    }

    .send-btn {
      border: none;
      border-radius: 8px;
      padding: 9px 12px;
      font-size: 0.7rem;
      font-weight: 700;
      color: #11111b;
      background: linear-gradient(135deg, #89b4fa, #cba6f7);
      cursor: pointer;
      min-width: 62px;
    }

    .send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .chat-error {
      margin-top: 8px;
      color: #f38ba8;
      font-size: 0.67rem;
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
    @Input() strategyMode: StrategyMode = 'long_term';

    private analyzerService = inject(MarketAnalyzerService);

    expanded = true;
    briefText = '';
    tags: { label: string; type: string }[] = [];
    chatMessages: ChatMessage[] = [];
    chatDraft = '';
    chatLoading = false;
    chatError: string | null = null;
    private sessionId = (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-copilot`);

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

    askPreset(question: string) {
        this.chatDraft = question;
        this.sendChat();
    }

    sendChat() {
        const question = this.chatDraft.trim();
        if (!question || this.chatLoading) {
            return;
        }

        const anchor = this.pickAnchorInstrument();
        const request: ChatRequest = {
            sessionId: this.sessionId,
            intent: this.resolveIntent(question),
            symbol: anchor?.symbol,
            question,
            strategyMode: this.strategyMode,
            analysisContext: this.buildAnalysisContext(anchor),
            history: this.chatMessages.slice(-8),
        };

        this.chatMessages.push({ role: 'user', content: question });
        this.chatDraft = '';
        this.chatLoading = true;
        this.chatError = null;

        this.analyzerService.chatWithCopilot(request).subscribe({
            next: (response: ChatResponse) => {
                this.chatMessages.push({ role: 'assistant', content: response.answer });
                this.chatLoading = false;
            },
            error: () => {
                this.chatLoading = false;
                this.chatError = 'Copilot is temporarily unavailable. Try again.';
            }
        });
    }

    private pickAnchorInstrument(): InstrumentAnalysis | null {
        if (!this.instruments?.length) {
            return null;
        }
        return this.instruments.find(i => i.trade_signal.trade_worthy) ?? this.instruments[0];
    }

    private resolveIntent(question: string): ChatRequest['intent'] {
        const q = question.toLowerCase();
        if (q.includes('risk') || q.includes('stop') || q.includes('size')) return 'risk_coach';
        if (q.includes('trigger') || q.includes('confirm') || q.includes('break')) return 'setup_monitor';
        if (q.includes('why') || q.includes('reason') || q.includes('score')) return 'signal_explainer';
        return 'general';
    }

    private buildAnalysisContext(anchor: InstrumentAnalysis | null): Record<string, unknown> {
        if (!anchor) {
            return {
                instrumentsTracked: this.instruments?.length ?? 0,
                marketSummary: {
                    bullish: this.instruments?.filter(i => i.trade_signal.recommendation === 'bullish').length ?? 0,
                    bearish: this.instruments?.filter(i => i.trade_signal.recommendation === 'bearish').length ?? 0,
                    tradeWorthy: this.instruments?.filter(i => i.trade_signal.trade_worthy).length ?? 0,
                }
            };
        }

        return {
            symbol: anchor.symbol,
            tradeSignal: anchor.trade_signal,
            blowoffTop: anchor.blowoff_top,
            volatility: anchor.volatility_risk,
            fundamentals: anchor.fundamentals,
            marketPhase: anchor.market_phase,
            pullbackWarning: anchor.pullback_warning,
            relativeStrength: anchor.relative_strength,
        };
    }
}
