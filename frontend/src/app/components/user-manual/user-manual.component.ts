import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-user-manual',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './user-manual.component.html',
    styleUrl: './user-manual.component.scss'
})
export class UserManualComponent {
    @Output() close = new EventEmitter<void>();

    sections = [
        {
            id: 'strategy',
            title: 'The Core Strategy',
            icon: '🏛️',
            content: `
        This analyzer uses a <strong>Multi-Timeframe Trend Following</strong> strategy. 
        It prioritizes safety and institutional-level risk management.
        <ul>
          <li><strong>Monthly Trend:</strong> We only look for long trades when the monthly trend is bullish (Price > 20MA).</li>
          <li><strong>Weekly Pullback:</strong> We seek entry points when a price pulls back to its weekly support, providing a better risk/reward.</li>
          <li><strong>Daily Confirmation:</strong> We use RSI and ADX to ensure there is active momentum before suggesting a trade.</li>
        </ul>
      `
        },
        {
            id: 'metrics',
            title: 'Understanding Metrics',
            icon: '📊',
            content: `
        <ul>
          <li><strong>Conviction Score:</strong> A scale of 0-100 based on how many technical conditions match our ideal "A+ Setup".</li>
          <li><strong>RSI (14):</strong> Measures overbought (>70) or oversold (<30) conditions. We look for "Rising Momentum".</li>
          <li><strong>ADX:</strong> Measures the strength of the trend. Above 25 indicates a strong, tradable trend.</li>
          <li><strong>ATR:</strong> Measures volatility. We use this to calculate where to place your Stop Loss fairly.</li>
        </ul>
      `
        },
        {
            id: 'risk',
            title: 'Risk & Position Sizing',
            icon: '🛡️',
            content: `
        Our AI calculates the exact amount to invest based on your portfolio value.
        <ul>
          <li><strong>Risk per Trade:</strong> Usually 1-2% of your total capital.</li>
          <li><strong>Correlation Penalty:</strong> If you are already holding similar assets (e.g., BTC and ETH), the AI reduces position size to prevent overexposure.</li>
          <li><strong>Hard Stops:</strong> Every recommendation comes with a mathematically derived Stop Loss to protect your capital.</li>
        </ul>
      `
        }
    ];

    activeSection = this.sections[0].id;
}
