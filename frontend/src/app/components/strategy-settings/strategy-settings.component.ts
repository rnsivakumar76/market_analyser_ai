import { Component, output, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarketAnalyzerService, StrategySettings } from '../../services/market-analyzer.service';

@Component({
  selector: 'app-strategy-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h2>Strategy Optimization</h2>
          <button class="close-btn" (click)="close.emit()">&times;</button>
        </div>
        
        <div class="modal-body">
          <p class="section-desc">Tune your algorithmic conviction thresholds and risk parameters.</p>
          
          <div class="settings-group">
            <div class="risk-section portfolio">
              <h3>Portfolio & Asset Allocation</h3>
              <div class="setting-item inline">
                <label>Account Balance ($)</label>
                <input type="number" [(ngModel)]="settings().portfolio_value" class="wide-input">
              </div>
              <div class="setting-item inline">
                <label>Max Risk per Trade (%)</label>
                <div class="input-row">
                    <input type="number" step="0.1" min="0.1" max="5" [(ngModel)]="settings().risk_per_trade_percent">
                    <span class="unit">%</span>
                </div>
              </div>
            </div>

            <div class="setting-item">
              <label>Conviction Threshold (0-100)</label>
              <div class="input-row">
                <input type="range" min="20" max="95" [(ngModel)]="settings().conviction_threshold" class="slider">
                <span class="value-tag">{{ settings().conviction_threshold }}</span>
              </div>
              <p class="help-text">Minimum score required to trigger a trade signal. Lower = more trades, Higher = more selective.</p>
            </div>

            <div class="setting-item">
              <label>ADX Strength Filter</label>
              <div class="input-row">
                <input type="range" min="10" max="40" [(ngModel)]="settings().adx_threshold" class="slider">
                <span class="value-tag">{{ settings().adx_threshold }}</span>
              </div>
              <p class="help-text">Minimum Trend Strength required. Markets below this are considered "Chop" and filtered out.</p>
            </div>

            <div class="risk-section">
              <h3>Risk Management (ATR Multipliers)</h3>
              <div class="setting-item inline">
                <label>Take Profit (TP)</label>
                <div class="input-row">
                    <input type="number" step="0.5" min="1" max="10" [(ngModel)]="settings().atr_multiplier_tp">
                    <span class="unit">x ATR</span>
                </div>
              </div>
              <div class="setting-item inline">
                <label>Stop Loss (SL)</label>
                <div class="input-row">
                    <input type="number" step="0.1" min="0.5" max="5" [(ngModel)]="settings().atr_multiplier_sl">
                    <span class="unit">x ATR</span>
                </div>
              </div>
            </div>
          </div>

          @if (saving()) {
            <div class="saving-overlay">
                <div class="spinner"></div>
                <span>Applying Strategy Updates...</span>
            </div>
          }
        </div>

        <div class="modal-footer">
          <button class="cancel-btn" (click)="close.emit()">Cancel</button>
          <button class="save-btn" (click)="save()">Apply & Recalculate</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(17, 17, 27, 0.85);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2000;
    }

    .modal-content {
      background: #1e1e2e;
      width: 90%;
      max-width: 500px;
      border-radius: 16px;
      border: 1px solid #313244;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
      overflow: hidden;
      position: relative;
    }

    .modal-header {
      padding: 20px 24px;
      border-bottom: 1px solid #313244;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .modal-header h2 {
      margin: 0;
      font-size: 1.25rem;
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

    .modal-body {
      padding: 24px;
      max-height: 70vh;
      overflow-y: auto;
    }

    .section-desc {
      color: #a6adc8;
      font-size: 0.9rem;
      margin-bottom: 24px;
    }

    .settings-group {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .setting-item label {
      display: block;
      font-size: 0.85rem;
      color: #9399b2;
      margin-bottom: 8px;
      font-weight: 600;
    }

    .input-row {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .slider {
      flex: 1;
      accent-color: #fab387;
    }

    .wide-input {
      background: #181825;
      border: 1px solid #45475a;
      color: #cdd6f4;
      padding: 6px 12px;
      border-radius: 6px;
      width: 120px;
      outline: none;
      text-align: right;
    }

    .value-tag {
      background: #313244;
      color: #fab387;
      padding: 4px 10px;
      border-radius: 6px;
      font-weight: 700;
      min-width: 40px;
      text-align: center;
    }

    .help-text {
      font-size: 0.75rem;
      color: #6c7086;
      margin: 4px 0 0 0;
    }

    .risk-section {
      background: rgba(69, 71, 90, 0.2);
      padding: 16px;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .risk-section h3 {
      font-size: 0.8rem;
      text-transform: uppercase;
      color: #fab387;
      margin: 0 0 8px 0;
      letter-spacing: 0.5px;
    }

    .setting-item.inline {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    
    .setting-item.inline label { margin: 0; }

    input[type="number"] {
      background: #181825;
      border: 1px solid #45475a;
      color: #cdd6f4;
      padding: 6px 12px;
      border-radius: 6px;
      width: 70px;
      outline: none;
    }

    .unit { font-size: 0.8rem; color: #6c7086; }

    .modal-footer {
      padding: 16px 24px;
      border-top: 1px solid #313244;
      background: #181825;
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }

    .cancel-btn {
      background: none;
      border: 1px solid #45475a;
      color: #a6adc8;
      padding: 10px 20px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.2s;
    }

    .save-btn {
      background: #fab387;
      color: #11111b;
      border: none;
      padding: 10px 24px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 700;
      transition: all 0.2s;
    }

    .save-btn:hover { background: #f9e2af; }

    .saving-overlay {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(30, 30, 46, 0.9);
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        gap: 16px; z-index: 10;
        color: #fab387; font-weight: 600;
    }

    .spinner {
        width: 32px; height: 32px;
        border: 3px solid #fab387;
        border-top-color: transparent;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class StrategySettingsComponent implements OnInit {
  private analyzerService = inject(MarketAnalyzerService);

  close = output();
  updated = output();

  settings = signal<StrategySettings>({
    conviction_threshold: 70,
    adx_threshold: 25,
    atr_multiplier_tp: 3.0,
    atr_multiplier_sl: 1.5,
    portfolio_value: 10000.0,
    risk_per_trade_percent: 1.0
  });

  saving = signal(false);

  ngOnInit() {
    this.analyzerService.getSettings().subscribe({
      next: (data) => this.settings.set(data),
      error: (err) => console.error('Failed to load settings', err)
    });
  }

  save() {
    this.saving.set(true);
    this.analyzerService.updateSettings(this.settings()).subscribe({
      next: () => {
        setTimeout(() => {
          this.saving.set(false);
          this.updated.emit();
          this.close.emit();
        }, 800);
      },
      error: (err) => {
        this.saving.set(false);
        console.error('Failed to save settings', err);
      }
    });
  }
}
