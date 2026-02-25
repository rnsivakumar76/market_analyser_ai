import { Component, Output, EventEmitter, Input, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { InstrumentAnalysis } from '../../services/market-analyzer.service';

interface AlertRule {
  id: string;
  type: 'score_threshold' | 'price_cross' | 'trade_worthy' | 'pullback_detected' | 'news_sentiment';
  symbol: string | null; // null = all symbols
  value: number;
  enabled: boolean;
  label: string;
}

interface AlertLog {
  id: string;
  ruleLabel: string;
  symbol: string;
  message: string;
  timestamp: string;
  read: boolean;
}

@Component({
  selector: 'app-smart-alerts',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="alerts-modal" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <div class="modal-title-area">
            <h2>🔔 Smart Alerts</h2>
            <span class="alert-status" [class]="notificationsEnabled ? 'on' : 'off'">
              {{ notificationsEnabled ? '● Notifications ON' : '○ Notifications OFF' }}
            </span>
          </div>
          <button class="close-btn" (click)="close.emit()">✕</button>
        </div>

        <!-- Enable Notifications -->
        @if (!notificationsEnabled) {
        <div class="enable-section">
          @if (notificationsBlocked) {
            <p class="https-warning">⚠️ Browser push notifications require HTTPS. Your site is on HTTP, so push notifications are unavailable. <strong>In-app alerts still work normally</strong> — check "Recent Alerts" below.</p>
          } @else {
            <p>Enable browser notifications to receive real-time alerts when market conditions match your rules.</p>
            <button class="enable-btn" (click)="enableNotifications()">🔔 Enable Notifications</button>
          }
        </div>
        }

        <!-- Active Rules -->
        <div class="rules-section">
          <div class="section-header">
            <h3>Alert Rules</h3>
            <button class="add-rule-btn" (click)="addRule()">+ Add Rule</button>
          </div>

          @for (rule of rules; track rule.id) {
          <div class="rule-row" [class.disabled]="!rule.enabled">
            <label class="rule-toggle">
              <input type="checkbox" [(ngModel)]="rule.enabled" (change)="saveRules()">
              <span class="toggle-slider"></span>
            </label>
            <div class="rule-config">
              <select [(ngModel)]="rule.type" (change)="updateRuleLabel(rule); saveRules()">
                <option value="score_threshold">Score ≥ Threshold</option>
                <option value="trade_worthy">Trade-Worthy Signal</option>
                <option value="pullback_detected">Pullback Warning</option>
                <option value="news_sentiment">Bearish News Alert</option>
              </select>
              @if (rule.type === 'score_threshold') {
                <input type="number" [(ngModel)]="rule.value" (change)="saveRules()" class="threshold-input" placeholder="Score">
              }
            </div>
            <span class="rule-label">{{ rule.label }}</span>
            <button class="rule-delete" (click)="removeRule(rule.id)">✕</button>
          </div>
          }

          @if (rules.length === 0) {
            <p class="no-rules">No alert rules configured. Add one to get started.</p>
          }
        </div>

        <!-- Alert History -->
        <div class="history-section">
          <div class="section-header">
            <h3>Recent Alerts</h3>
            @if (alertHistory.length > 0) {
              <button class="clear-btn" (click)="clearHistory()">Clear All</button>
            }
          </div>

          <div class="history-list">
            @for (alert of alertHistory; track alert.id) {
            <div class="alert-item" [class.unread]="!alert.read" (click)="alert.read = true">
              <div class="alert-icon">🔔</div>
              <div class="alert-body">
                <span class="alert-rule">{{ alert.ruleLabel }}</span>
                <span class="alert-message">{{ alert.message }}</span>
              </div>
              <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
            </div>
            } @empty {
              <p class="no-alerts">No alerts triggered yet.</p>
            }
          </div>
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

    .alerts-modal {
      background: #1e1e2e;
      border: 1px solid #313244;
      border-radius: 16px;
      width: 90%;
      max-width: 700px;
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

    .alert-status {
      font-size: 0.7rem;
      font-weight: 700;
    }

    .alert-status.on { color: #a6e3a1; }
    .alert-status.off { color: #f38ba8; }

    .close-btn {
      background: none;
      border: none;
      color: #6c7086;
      font-size: 1.2rem;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
    }

    .close-btn:hover { background: #313244; color: #cdd6f4; }

    .enable-section {
      padding: 20px 24px;
      text-align: center;
      border-bottom: 1px solid #313244;
      background: rgba(243,139,168,0.05);

      p {
        color: #a6adc8;
        font-size: 0.88rem;
        margin: 0 0 14px;
      }
    }

    .enable-btn {
      background: linear-gradient(135deg, #cba6f7, #89b4fa);
      color: #11111b;
      border: none;
      padding: 10px 24px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 0.88rem;
      cursor: pointer;
      transition: opacity 0.2s;

      &:hover { opacity: 0.9; }
    }

    .https-warning {
      color: #f9e2af;
      font-size: 0.82rem;
      line-height: 1.5;
      margin: 0;
      padding: 4px 0;
    }

    .rules-section, .history-section {
      padding: 16px 24px;
      border-bottom: 1px solid #313244;
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      h3 {
        color: #cdd6f4;
        font-size: 0.9rem;
        font-weight: 700;
        margin: 0;
      }
    }

    .add-rule-btn, .clear-btn {
      background: transparent;
      border: 1px dashed #45475a;
      color: #89b4fa;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 6px;
      cursor: pointer;

      &:hover { border-color: #89b4fa; }
    }

    .rule-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px 12px;
      background: rgba(17,17,27,0.4);
      border-radius: 8px;
      border: 1px solid #313244;
      margin-bottom: 8px;
      transition: opacity 0.2s;

      &.disabled { opacity: 0.5; }
    }

    .rule-toggle {
      position: relative;
      width: 36px;
      height: 20px;
      flex-shrink: 0;

      input {
        opacity: 0;
        width: 0;
        height: 0;
      }

      .toggle-slider {
        position: absolute;
        inset: 0;
        background: #313244;
        border-radius: 20px;
        cursor: pointer;
        transition: background 0.2s;

        &::before {
          content: '';
          position: absolute;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #6c7086;
          left: 2px;
          top: 2px;
          transition: all 0.2s;
        }
      }

      input:checked + .toggle-slider {
        background: #89b4fa;

        &::before {
          background: #11111b;
          transform: translateX(16px);
        }
      }
    }

    .rule-config {
      display: flex;
      gap: 8px;
      align-items: center;

      select, .threshold-input {
        background: #11111b;
        border: 1px solid #313244;
        color: #cdd6f4;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.78rem;

        &:focus { outline: none; border-color: #89b4fa; }
      }

      .threshold-input { width: 60px; }
    }

    .rule-label {
      flex: 1;
      font-size: 0.72rem;
      color: #6c7086;
      font-style: italic;
    }

    .rule-delete {
      background: none;
      border: none;
      color: #585b70;
      cursor: pointer;
      font-size: 0.8rem;
      padding: 2px 6px;
      border-radius: 4px;

      &:hover { background: rgba(243,139,168,0.1); color: #f38ba8; }
    }

    .no-rules, .no-alerts {
      text-align: center;
      color: #6c7086;
      font-size: 0.85rem;
      padding: 16px 0;
    }

    .history-list {
      max-height: 200px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .alert-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      background: rgba(17,17,27,0.3);
      border-radius: 6px;
      border: 1px solid #313244;
      cursor: pointer;
      transition: background 0.2s;

      &.unread {
        background: rgba(137,180,250,0.05);
        border-color: rgba(137,180,250,0.15);
      }

      &:hover { background: rgba(17,17,27,0.5); }
    }

    .alert-icon { font-size: 0.9rem; }

    .alert-body {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    .alert-rule {
      font-size: 0.7rem;
      font-weight: 700;
      color: #89b4fa;
    }

    .alert-message {
      font-size: 0.8rem;
      color: #cdd6f4;
    }

    .alert-time {
      font-size: 0.65rem;
      color: #585b70;
      white-space: nowrap;
    }

    @media (max-width: 600px) {
      .alerts-modal { width: 95%; max-height: 90vh; }
      .rule-row { flex-wrap: wrap; }
    }
  `]
})
export class SmartAlertsComponent implements OnInit {
  @Input() instruments: InstrumentAnalysis[] = [];
  @Output() close = new EventEmitter<void>();

  notificationsEnabled = false;
  notificationsBlocked = false;
  rules: AlertRule[] = [];
  alertHistory: AlertLog[] = [];

  private STORAGE_KEY = 'market_analyzer_alert_rules';
  private HISTORY_KEY = 'market_analyzer_alert_history';

  ngOnInit() {
    // Check if Notification API is available (requires HTTPS)
    if ('Notification' in window && window.isSecureContext) {
      this.notificationsEnabled = Notification.permission === 'granted';
    } else {
      this.notificationsBlocked = true;
    }
    this.loadRules();
    this.loadHistory();
    this.evaluate();
  }

  enableNotifications() {
    if (!('Notification' in window) || !window.isSecureContext) {
      this.notificationsBlocked = true;
      return;
    }
    Notification.requestPermission().then(perm => {
      this.notificationsEnabled = perm === 'granted';
      if (perm === 'denied') {
        this.notificationsBlocked = true;
      }
    }).catch(() => {
      this.notificationsBlocked = true;
    });
  }

  addRule() {
    const rule: AlertRule = {
      id: Date.now().toString(),
      type: 'trade_worthy',
      symbol: null,
      value: 50,
      enabled: true,
      label: 'Alerts when a trade-worthy signal appears'
    };
    this.rules.push(rule);
    this.saveRules();
  }

  removeRule(id: string) {
    this.rules = this.rules.filter(r => r.id !== id);
    this.saveRules();
  }

  updateRuleLabel(rule: AlertRule) {
    switch (rule.type) {
      case 'score_threshold': rule.label = `Score ≥ ${rule.value}`; break;
      case 'trade_worthy': rule.label = 'Trade-worthy signal detected'; break;
      case 'pullback_detected': rule.label = 'Pullback warning triggered'; break;
      case 'news_sentiment': rule.label = 'Bearish news sentiment alert'; break;
      default: rule.label = '';
    }
  }

  saveRules() {
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.rules));
  }

  loadRules() {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      this.rules = stored ? JSON.parse(stored) : [];
    } catch { this.rules = []; }
  }

  loadHistory() {
    try {
      const stored = localStorage.getItem(this.HISTORY_KEY);
      this.alertHistory = stored ? JSON.parse(stored) : [];
    } catch { this.alertHistory = []; }
  }

  saveHistory() {
    // Keep only latest 50
    this.alertHistory = this.alertHistory.slice(0, 50);
    localStorage.setItem(this.HISTORY_KEY, JSON.stringify(this.alertHistory));
  }

  clearHistory() {
    this.alertHistory = [];
    localStorage.removeItem(this.HISTORY_KEY);
  }

  evaluate() {
    if (!this.instruments || this.instruments.length === 0) return;

    const activeRules = this.rules.filter(r => r.enabled);
    for (const rule of activeRules) {
      for (const instrument of this.instruments) {
        let triggered = false;
        let message = '';

        switch (rule.type) {
          case 'score_threshold':
            if (Math.abs(instrument.trade_signal.score) >= rule.value) {
              triggered = true;
              message = `${instrument.symbol} has score ${instrument.trade_signal.score} (threshold: ${rule.value})`;
            }
            break;
          case 'trade_worthy':
            if (instrument.trade_signal.trade_worthy) {
              triggered = true;
              message = `${instrument.symbol} is now trade-worthy (${instrument.trade_signal.recommendation}, score ${instrument.trade_signal.score})`;
            }
            break;
          case 'pullback_detected':
            if (instrument.pullback_warning?.is_warning) {
              triggered = true;
              message = `Pullback detected in ${instrument.symbol}: ${instrument.pullback_warning.description}`;
            }
            break;
          case 'news_sentiment':
            if (instrument.news_sentiment?.label === 'Bearish') {
              triggered = true;
              message = `Bearish news for ${instrument.symbol}: ${instrument.news_sentiment.sentiment_summary}`;
            }
            break;
        }

        if (triggered) {
          // Deduplicate: don't re-alert same message in last 1 hour
          const isDuplicate = this.alertHistory.some(a =>
            a.symbol === instrument.symbol &&
            a.ruleLabel === rule.label &&
            (Date.now() - new Date(a.timestamp).getTime()) < 3600000
          );

          if (!isDuplicate) {
            const alert: AlertLog = {
              id: Date.now().toString() + instrument.symbol,
              ruleLabel: rule.label,
              symbol: instrument.symbol,
              message,
              timestamp: new Date().toISOString(),
              read: false
            };
            this.alertHistory.unshift(alert);
            this.sendBrowserNotification(instrument.symbol, message);
          }
        }
      }
    }
    this.saveHistory();
  }

  private sendBrowserNotification(symbol: string, message: string) {
    if (this.notificationsEnabled && 'Notification' in window) {
      new Notification(`Market Analyzer — ${symbol}`, {
        body: message,
        icon: '🔔',
        tag: symbol
      });
    }
  }

  formatTime(timestamp: string): string {
    const d = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h ago`;
    return d.toLocaleDateString();
  }
}
