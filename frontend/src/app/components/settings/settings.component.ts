import { Component, signal, inject, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarketAnalyzerService } from '../../services/market-analyzer.service';

@Component({
    selector: 'app-settings',
    standalone: true,
    imports: [CommonModule, FormsModule],
    template: `
    <div class="settings-backdrop" (click)="close.emit()">
      <div class="settings-modal" (click)="$event.stopPropagation()">
        <header class="settings-header">
          <h2>Manage Symbols</h2>
          <button class="close-btn" (click)="close.emit()">&times;</button>
        </header>

        <section class="add-symbol-section">
          <h3>Add New Symbol</h3>
          <div class="input-group">
            <input 
              type="text" 
              [(ngModel)]="newSymbol" 
              placeholder="Ticker (e.g. TSLA)" 
              [disabled]="isAdding()"
              (keyup.enter)="addInstrument()"
            >
            <input 
              type="text" 
              [(ngModel)]="newName" 
              placeholder="Name (e.g. Tesla Inc)" 
              [disabled]="isAdding()"
              (keyup.enter)="addInstrument()"
            >
            <button class="add-btn" (click)="addInstrument()" [disabled]="!newSymbol || !newName || isAdding()">
              {{ isAdding() ? 'Adding...' : 'Add' }}
            </button>
          </div>
          @if (addError()) {
            <p class="error-text">{{ addError() }}</p>
          }
        </section>

        <section class="instruments-list-section">
          <h3>Current Symbols</h3>
          @if (isLoading()) {
            <div class="loader">Loading symbols...</div>
          } @else {
            <div class="instruments-list">
              @for (inst of instruments(); track inst.symbol) {
                <div class="instrument-item">
                  <div class="inst-info">
                    <span class="inst-symbol">{{ inst.symbol }}</span>
                    <span class="inst-name">{{ inst.name }}</span>
                  </div>
                  <button class="delete-btn" (click)="deleteInstrument(inst.symbol)" [disabled]="isDeleting() === inst.symbol">
                    {{ isDeleting() === inst.symbol ? '...' : '&times;' }}
                  </button>
                </div>
              }
            </div>
          }
        </section>
      </div>
    </div>
  `,
    styles: [`
    .settings-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.7);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      backdrop-filter: blur(5px);
    }

    .settings-modal {
      background: #1e1e2e;
      width: 90%;
      max-width: 500px;
      border-radius: 12px;
      padding: 24px;
      border: 1px solid #313244;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    }

    .settings-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      border-bottom: 1px solid #313244;
      padding-bottom: 12px;
    }

    .settings-header h2 {
      margin: 0;
      color: #cdd6f4;
    }

    .close-btn {
      background: none;
      border: none;
      color: #6c7086;
      font-size: 2rem;
      cursor: pointer;
      line-height: 1;
    }

    .close-btn:hover { color: #f38ba8; }

    h3 {
      color: #cba6f7;
      font-size: 1rem;
      margin-bottom: 12px;
    }

    .input-group {
      display: grid;
      grid-template-columns: 1fr 1.5fr auto;
      gap: 8px;
      margin-bottom: 16px;
    }

    input {
      background: #181825;
      border: 1px solid #313244;
      border-radius: 6px;
      padding: 8px 12px;
      color: #cdd6f4;
    }

    input:focus {
      outline: none;
      border-color: #cba6f7;
    }

    .add-btn {
      background: #cba6f7;
      color: #1e1e2e;
      border: none;
      border-radius: 6px;
      padding: 8px 16px;
      font-weight: 700;
      cursor: pointer;
    }

    .add-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .error-text {
      color: #f38ba8;
      font-size: 0.85rem;
      margin-top: -8px;
      margin-bottom: 16px;
    }

    .instruments-list {
      max-height: 300px;
      overflow-y: auto;
      border: 1px solid #313244;
      border-radius: 6px;
      background: #181825;
    }

    .instrument-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      border-bottom: 1px solid #313244;
    }

    .instrument-item:last-child { border-bottom: none; }

    .inst-info {
      display: flex;
      flex-direction: column;
    }

    .inst-symbol {
      font-weight: 700;
      color: #cdd6f4;
      font-size: 1rem;
    }

    .inst-name {
      font-size: 0.8rem;
      color: #6c7086;
    }

    .delete-btn {
      background: rgba(243, 139, 168, 0.1);
      color: #f38ba8;
      border: 1px solid rgba(243, 139, 168, 0.2);
      border-radius: 4px;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.2rem;
      cursor: pointer;
    }

    .delete-btn:hover {
      background: #f38ba8;
      color: #1e1e2e;
    }

    .delete-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .loader {
      text-align: center;
      color: #6c7086;
      padding: 20px;
    }
  `]
})
export class SettingsComponent {
    private analyzerService = inject(MarketAnalyzerService);

    @Output() close = new EventEmitter<void>();
    @Output() updated = new EventEmitter<void>();

    instruments = signal<{ symbol: string; name: string }[]>([]);
    isLoading = signal(true);
    isAdding = signal(false);
    isDeleting = signal<string | null>(null);
    addError = signal<string | null>(null);

    newSymbol = '';
    newName = '';

    constructor() {
        this.loadInstruments();
    }

    loadInstruments() {
        this.isLoading.set(true);
        this.analyzerService.getInstruments().subscribe({
            next: (data) => {
                this.instruments.set(data.instruments);
                this.isLoading.set(false);
            },
            error: () => this.isLoading.set(false)
        });
    }

    addInstrument() {
        if (!this.newSymbol || !this.newName) return;

        this.isAdding.set(true);
        this.addError.set(null);

        this.analyzerService.addInstrument(this.newSymbol, this.newName).subscribe({
            next: (response) => {
                this.instruments.set(response.instruments);
                this.newSymbol = '';
                this.newName = '';
                this.isAdding.set(false);
                this.updated.emit();
            },
            error: (err) => {
                this.addError.set(err.error?.detail || 'Failed to add symbol. Invalid ticker?');
                this.isAdding.set(false);
            }
        });
    }

    deleteInstrument(symbol: string) {
        if (confirm(`Are you sure you want to remove ${symbol}?`)) {
            this.isDeleting.set(symbol);
            this.analyzerService.deleteInstrument(symbol).subscribe({
                next: (response) => {
                    this.instruments.set(response.instruments);
                    this.isDeleting.set(null);
                    this.updated.emit();
                },
                error: () => this.isDeleting.set(null)
            });
        }
    }
}
