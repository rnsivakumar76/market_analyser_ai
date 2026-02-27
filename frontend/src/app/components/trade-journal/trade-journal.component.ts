import { Component, Output, EventEmitter, OnInit, inject, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarketAnalyzerService } from '../../services/market-analyzer.service';

@Component({
  selector: 'app-trade-journal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="journal-modal" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <div class="modal-title-area">
            <h2>📒 Trade Journal</h2>
            <span class="trade-count">{{ trades.length }} trades logged</span>
          </div>
          <button class="close-btn" (click)="close.emit()">✕</button>
        </div>

        <!-- Add Trade Form -->
        <div class="add-trade-section" [class.expanded]="showAddForm">
          <button class="add-trade-toggle" (click)="showAddForm = !showAddForm">
            {{ showAddForm ? '▼ Close Form' : '+ Log New Trade' }}
          </button>

          @if (showAddForm) {
          <form class="trade-form" (submit)="submitTrade($event)">
            <div class="form-row">
              <div class="form-group">
                <label>Symbol</label>
                <input type="text" [(ngModel)]="newTrade.symbol" name="symbol" placeholder="AAPL" required>
              </div>
              <div class="form-group">
                <label>Direction</label>
                <select [(ngModel)]="newTrade.direction" name="direction">
                  <option value="long">Long</option>
                  <option value="short">Short</option>
                </select>
              </div>
              <div class="form-group">
                <label>Entry Price</label>
                <input type="number" [(ngModel)]="newTrade.entry_price" name="entry" step="0.01" required>
              </div>
              <div class="form-group">
                <label>Exit Price</label>
                <input type="number" [(ngModel)]="newTrade.exit_price" name="exit" step="0.01">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Position Size</label>
                <input type="number" [(ngModel)]="newTrade.size" name="size" step="0.01" placeholder="Units">
              </div>
              <div class="form-group">
                <label>Date</label>
                <input type="date" [(ngModel)]="newTrade.date" name="date">
              </div>
              <div class="form-group full">
                <label>Notes</label>
                <input type="text" [(ngModel)]="newTrade.notes" name="notes" placeholder="Trade thesis, lessons...">
              </div>
            </div>
            <div class="form-actions">
              <span class="pnl-preview" [class]="previewPnl >= 0 ? 'positive' : 'negative'">
                PnL: {{ previewPnl >= 0 ? '+' : '' }}{{ previewPnl.toFixed(2) }}%
              </span>
              <button type="submit" class="submit-btn" [disabled]="!newTrade.symbol || !newTrade.entry_price || saving">
                {{ saving ? '⏳ Saving...' : '💾 Save Trade' }}
              </button>
            </div>
            @if (errorMsg) {
              <div class="error-banner">❌ {{ errorMsg }}</div>
            }
          </form>
          }
        </div>

        <!-- Journal Stats -->
        @if (trades.length > 0) {
        <div class="journal-stats">
          <div class="jstat">
            <span class="jstat-label">Total Trades</span>
            <span class="jstat-value">{{ trades.length }}</span>
          </div>
          <div class="jstat">
            <span class="jstat-label">Win Rate</span>
            <span class="jstat-value" [class]="winRate >= 50 ? 'good' : 'bad'">{{ winRate.toFixed(0) }}%</span>
          </div>
          <div class="jstat">
            <span class="jstat-label">Total PnL</span>
            <span class="jstat-value" [class]="totalPnl >= 0 ? 'good' : 'bad'">
              {{ totalPnl >= 0 ? '+' : '' }}{{ totalPnl.toFixed(2) }}%
            </span>
          </div>
          <div class="jstat">
            <span class="jstat-label">Best Trade</span>
            <span class="jstat-value good">{{ bestTrade }}</span>
          </div>
          <div class="jstat">
            <span class="jstat-label">Worst Trade</span>
            <span class="jstat-value bad">{{ worstTrade }}</span>
          </div>
        </div>
        }

        <!-- Trades List -->
        <div class="trades-list">
          @if (loading) {
            <div class="loading-msg">Loading journal...</div>
          } @else if (trades.length === 0) {
            <div class="empty-journal">
              <span class="ej-icon">📓</span>
              <p>No trades logged yet. Start by clicking "Log New Trade" above.</p>
            </div>
          } @else {
            @for (trade of trades; track trade.id) {
            <div class="trade-row" [class]="trade.direction">
              <div class="trade-main">
                <span class="trade-symbol">{{ trade.symbol }}</span>
                <span class="trade-dir-badge" [class]="trade.direction">{{ trade.direction?.toUpperCase() }}</span>
                <span class="trade-date">{{ trade.date || trade.created_at?.slice(0,10) }}</span>
              </div>
              <div class="trade-prices">
                <span class="tp-label">Entry:</span>
                <span class="tp-value">\${{ trade.entry_price }}</span>
                @if (trade.exit_price) {
                  <span class="tp-label">Exit:</span>
                  <span class="tp-value">\${{ trade.exit_price }}</span>
                  <span class="trade-pnl" [class]="getTradePnl(trade) >= 0 ? 'good' : 'bad'">
                    {{ getTradePnl(trade) >= 0 ? '+' : '' }}{{ getTradePnl(trade).toFixed(2) }}%
                  </span>
                } @else {
                  <span class="tp-open">OPEN</span>
                }
              </div>
              @if (trade.notes) {
                <div class="trade-notes">{{ trade.notes }}</div>
              }
              <button class="trade-delete" (click)="deleteTrade(trade.id)" title="Delete">🗑️</button>
            </div>
            }
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 5000;
      backdrop-filter: blur(4px);
    }

    .journal-modal {
      background: #1e1e2e;
      border: 1px solid #313244;
      border-radius: 16px;
      width: 90%;
      max-width: 880px;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 60px rgba(0,0,0,0.5);
      animation: slide-up 0.3s ease-out;
    }

    @keyframes slide-up {
      from { opacity: 0; transform: translateY(24px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px 24px;
      border-bottom: 1px solid #313244;
    }

    .modal-title-area h2 {
      color: #cdd6f4;
      font-size: 1.2rem;
      margin: 0;
    }

    .trade-count {
      font-size: 0.75rem;
      color: #6c7086;
    }

    .close-btn {
      background: none;
      border: none;
      color: #6c7086;
      font-size: 1.2rem;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      transition: all 0.2s;
    }

    .close-btn:hover { background: #313244; color: #cdd6f4; }

    .add-trade-section {
      padding: 12px 24px;
      border-bottom: 1px solid #313244;
    }

    .add-trade-toggle {
      background: transparent;
      border: 1px dashed #45475a;
      color: #89b4fa;
      font-size: 0.82rem;
      font-weight: 700;
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
      width: 100%;
      transition: all 0.2s;
    }

    .add-trade-toggle:hover { border-color: #89b4fa; }

    .trade-form {
      margin-top: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .form-row {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
      min-width: 120px;

      label {
        font-size: 0.65rem;
        color: #6c7086;
        font-weight: 700;
        text-transform: uppercase;
      }

      input, select {
        background: #11111b;
        border: 1px solid #313244;
        color: #cdd6f4;
        padding: 8px 10px;
        border-radius: 6px;
        font-size: 0.85rem;

        &:focus { outline: none; border-color: #89b4fa; }
      }

      &.full { flex: 2; }
    }

    .form-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .pnl-preview {
      font-size: 0.85rem;
      font-weight: 700;
    }

    .pnl-preview.positive { color: #a6e3a1; }
    .pnl-preview.negative { color: #f38ba8; }

    .submit-btn {
      background: #89b4fa;
      color: #11111b;
      border: none;
      padding: 8px 20px;
      border-radius: 8px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s;

      &:hover:not(:disabled) { background: #b4befe; }
      &:disabled { opacity: 0.5; cursor: not-allowed; }
    }

    .journal-stats {
      display: flex;
      gap: 20px;
      padding: 14px 24px;
      border-bottom: 1px solid #313244;
      background: rgba(17,17,27,0.3);
      flex-wrap: wrap;
    }

    .jstat {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .jstat-label {
      font-size: 0.6rem;
      font-weight: 700;
      color: #6c7086;
      text-transform: uppercase;
    }

    .jstat-value {
      font-size: 0.95rem;
      font-weight: 700;
      color: #cdd6f4;
      &.good { color: #a6e3a1; }
      &.bad { color: #f38ba8; }
    }

    .trades-list {
      flex: 1;
      overflow-y: auto;
      padding: 12px 24px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .trade-row {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 10px 14px;
      background: rgba(17,17,27,0.4);
      border-radius: 8px;
      border: 1px solid #313244;
      position: relative;
      flex-wrap: wrap;

      &.long { border-left: 3px solid #a6e3a1; }
      &.short { border-left: 3px solid #f38ba8; }
    }

    .trade-main {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .trade-symbol {
      font-weight: 800;
      color: #cdd6f4;
      font-size: 0.95rem;
    }

    .trade-dir-badge {
      font-size: 0.6rem;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 3px;
      &.long { background: rgba(166,227,161,0.15); color: #a6e3a1; }
      &.short { background: rgba(243,139,168,0.15); color: #f38ba8; }
    }

    .trade-date {
      font-size: 0.75rem;
      color: #6c7086;
    }

    .trade-prices {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-left: auto;
    }

    .tp-label {
      font-size: 0.65rem;
      color: #585b70;
      text-transform: uppercase;
    }

    .tp-value {
      font-size: 0.85rem;
      color: #cdd6f4;
      font-weight: 600;
    }

    .trade-pnl {
      font-weight: 800;
      font-size: 0.9rem;
      padding: 2px 8px;
      border-radius: 4px;
      &.good { background: rgba(166,227,161,0.1); color: #a6e3a1; }
      &.bad { background: rgba(243,139,168,0.1); color: #f38ba8; }
    }

    .tp-open {
      font-size: 0.65rem;
      font-weight: 800;
      padding: 2px 6px;
      color: #f9e2af;
      background: rgba(249,226,175,0.15);
      border-radius: 3px;
    }

    .trade-notes {
      width: 100%;
      font-size: 0.75rem;
      color: #a6adc8;
      font-style: italic;
      padding-top: 4px;
      border-top: 1px dashed #313244;
    }

    .trade-delete {
      position: absolute;
      top: 8px;
      right: 8px;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 0.8rem;
      opacity: 0;
      transition: opacity 0.2s;
    }

    .trade-row:hover .trade-delete { opacity: 1; }

    .loading-msg, .empty-journal {
      text-align: center;
      padding: 40px;
      color: #6c7086;
    }

    .ej-icon { font-size: 2.5rem; margin-bottom: 12px; display: block; }
    .empty-journal p { font-size: 0.9rem; }

    @media (max-width: 600px) {
      .journal-modal { width: 95%; max-height: 90vh; }
      .form-row { flex-direction: column; }
      .trade-prices { margin-left: 0; }
      .journal-stats { gap: 12px; padding: 10px 16px; }
    }

    .error-banner {
      background: rgba(243,139,168,0.1);
      border: 1px solid rgba(243,139,168,0.3);
      color: #f38ba8;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 0.8rem;
      margin-top: 8px;
    }
  `]
})
export class TradeJournalComponent implements OnInit {
  @Output() close = new EventEmitter<void>();
  @Input() prefill: any = null;
  private service = inject(MarketAnalyzerService);

  trades: any[] = [];
  loading = true;
  saving = false;
  errorMsg = '';
  showAddForm = false;
  newTrade: any = { symbol: '', direction: 'long', entry_price: null, exit_price: null, size: null, date: '', notes: '' };

  ngOnInit() {
    if (this.prefill) {
      this.newTrade = { ...this.newTrade, ...this.prefill };
      this.showAddForm = true;
    }
    this.service.getJournal().subscribe({
      next: (data) => { this.trades = data.reverse(); this.loading = false; },
      error: (err) => { this.loading = false; console.error('Journal load error:', err); }
    });
  }

  get previewPnl(): number {
    if (!this.newTrade.entry_price || !this.newTrade.exit_price) return 0;
    const pnl = ((this.newTrade.exit_price - this.newTrade.entry_price) / this.newTrade.entry_price) * 100;
    return this.newTrade.direction === 'short' ? -pnl : pnl;
  }

  get winRate(): number {
    const closed = this.trades.filter(t => t.exit_price);
    if (closed.length === 0) return 0;
    const wins = closed.filter(t => this.getTradePnl(t) > 0).length;
    return (wins / closed.length) * 100;
  }

  get totalPnl(): number {
    return this.trades.filter(t => t.exit_price).reduce((sum, t) => sum + this.getTradePnl(t), 0);
  }

  get bestTrade(): string {
    const closed = this.trades.filter(t => t.exit_price);
    if (closed.length === 0) return 'N/A';
    const best = closed.reduce((a, b) => this.getTradePnl(a) > this.getTradePnl(b) ? a : b);
    return `${best.symbol} +${this.getTradePnl(best).toFixed(1)}%`;
  }

  get worstTrade(): string {
    const closed = this.trades.filter(t => t.exit_price);
    if (closed.length === 0) return 'N/A';
    const worst = closed.reduce((a, b) => this.getTradePnl(a) < this.getTradePnl(b) ? a : b);
    return `${worst.symbol} ${this.getTradePnl(worst).toFixed(1)}%`;
  }

  getTradePnl(trade: any): number {
    if (!trade.entry_price || !trade.exit_price) return 0;
    const pnl = ((trade.exit_price - trade.entry_price) / trade.entry_price) * 100;
    return trade.direction === 'short' ? -pnl : pnl;
  }

  submitTrade(event: Event) {
    event.preventDefault();
    this.errorMsg = '';
    this.saving = true;
    if (!this.newTrade.date) {
      this.newTrade.date = new Date().toISOString().slice(0, 10);
    }
    this.service.addTrade({ ...this.newTrade }).subscribe({
      next: (res) => {
        this.trades.unshift(res.trade);
        this.newTrade = { symbol: '', direction: 'long', entry_price: null, exit_price: null, size: null, date: '', notes: '' };
        this.showAddForm = false;
        this.saving = false;
      },
      error: (err) => {
        this.saving = false;
        this.errorMsg = err?.error?.detail || err?.message || 'Failed to save trade. Check your connection.';
        console.error('Save trade error:', err);
      }
    });
  }

  deleteTrade(id: string) {
    this.service.deleteTrade(id).subscribe({
      next: () => { this.trades = this.trades.filter(t => t.id !== id); },
      error: (err) => { console.error('Delete trade error:', err); }
    });
  }
}
