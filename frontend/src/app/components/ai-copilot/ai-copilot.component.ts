import { Component, Input, OnChanges, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
    ChatMessage,
    ChatRequest,
    ChatResponse,
    InstrumentAnalysis,
    MarketAnalyzerService,
    StrategyMode,
} from '../../services/market-analyzer.service';

@Component({
    selector: 'app-ai-copilot',
    standalone: true,
    imports: [CommonModule, FormsModule],
    template: `
    <div class="copilot-panel">
      <div class="chat-panel-header">AI CHAT COPILOT</div>
      <div class="chat-subheader">
        @if (selectedInstrument; as inst) {
          {{ inst.symbol }} • {{ strategyMode === 'long_term' ? 'Long-term' : 'Short-term' }} context
        } @else {
          Select an instrument to start contextual chat
        }
      </div>

      @if (chatModeHint) {
        <div class="chat-hint">{{ chatModeHint }}</div>
      }

      <div class="quick-actions">
        <button type="button" class="quick-btn" (click)="askPreset('Why is this setup trade-worthy now?')">Why now?</button>
        <button type="button" class="quick-btn" (click)="askPreset('What is the key risk and invalidation level?')">Main risk</button>
        <button type="button" class="quick-btn" (click)="askPreset('What confirms the bigger move?')">Big move trigger</button>
      </div>

      <div class="chat-log">
        @for (msg of chatMessages; track $index) {
          <div class="chat-msg" [class.user]="msg.role === 'user'" [class.assistant]="msg.role === 'assistant'">
            <span class="chat-role">{{ msg.role === 'user' ? 'You' : 'Copilot' }}</span>
            <span class="chat-content">{{ msg.content }}</span>
          </div>
        }
        @if (chatLoading) {
          <div class="chat-msg assistant"><span class="chat-role">Copilot</span><span class="chat-content">Thinking...</span></div>
        }
      </div>

      <div class="chat-compose">
        <textarea
          [(ngModel)]="chatDraft"
          rows="2"
          maxlength="600"
          placeholder="Ask about this selected instrument setup, risk, or trigger confirmation..."
        ></textarea>
        <button type="button" class="send-btn" (click)="sendChat()" [disabled]="chatLoading || !chatDraft.trim() || !selectedInstrument">Send</button>
      </div>
      @if (chatError) {
        <div class="chat-error">{{ chatError }}</div>
      }
    </div>
  `,
    styles: [`
    .copilot-panel {
      background: #1e1e2e;
      border: 1px solid #313244;
      border-radius: 10px;
      padding: 12px;
    }

    .chat-panel-header {
      font-size: 0.66rem;
      letter-spacing: 1.1px;
      font-weight: 800;
      color: #89b4fa;
      margin-bottom: 6px;
      text-transform: uppercase;
    }

    .chat-subheader {
      font-size: 0.6rem;
      color: #9399b2;
      margin-bottom: 8px;
    }

    .quick-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }

    .chat-hint {
      margin-bottom: 8px;
      padding: 6px 8px;
      border-radius: 6px;
      border: 1px solid rgba(249, 226, 175, 0.35);
      background: rgba(249, 226, 175, 0.08);
      color: #f9e2af;
      font-size: 0.65rem;
      line-height: 1.35;
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

    .chat-content {
      white-space: pre-line;
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

  `]
})
export class AiCopilotComponent implements OnChanges {
    @Input() selectedInstrument: InstrumentAnalysis | null = null;
    @Input() strategyMode: StrategyMode = 'long_term';

    private analyzerService = inject(MarketAnalyzerService);

    chatMessages: ChatMessage[] = [];
    chatDraft = '';
    chatLoading = false;
    chatError: string | null = null;
    chatModeHint: string | null = null;
    private activeSymbol: string | null = null;
    private sessionId = (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-copilot`);

    ngOnChanges(changes: SimpleChanges) {
        if (changes['selectedInstrument']) {
            const nextSymbol = this.selectedInstrument?.symbol ?? null;
            if (this.activeSymbol !== nextSymbol) {
                this.resetConversation();
                this.activeSymbol = nextSymbol;
            }
        }
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

        const anchor = this.selectedInstrument;
        if (!anchor) {
            this.chatError = 'Select an instrument first to get contextual chat guidance.';
            return;
        }
        const request: ChatRequest = {
            sessionId: this.sessionId,
            intent: this.resolveIntent(question),
            symbol: anchor?.symbol,
            question,
            strategyMode: this.strategyMode,
            analysisContext: this.buildAnalysisContext(anchor),
            history: [],
        };

        this.chatMessages.push({ role: 'user', content: question });
        this.chatDraft = '';
        this.chatLoading = true;
        this.chatError = null;

        this.analyzerService.chatWithCopilot(request).subscribe({
            next: (response: ChatResponse) => {
                this.chatModeHint = response.modelUsed === 'fallback-context-only'
                    ? 'Live model temporarily unavailable. Using context-only copilot mode.'
                    : null;
                this.chatMessages.push({ role: 'assistant', content: response.answer });
                this.chatLoading = false;
            },
            error: () => {
                this.chatLoading = false;
                this.chatError = 'Copilot is temporarily unavailable. Try again.';
            }
        });
    }

    private resetConversation() {
        this.chatMessages = [];
        this.chatDraft = '';
        this.chatLoading = false;
        this.chatError = null;
        this.chatModeHint = null;
        this.sessionId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-copilot`;
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
            return {};
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
