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
      id: 'dashboard',
      title: 'Navigation & Dashboard',
      icon: '📊',
      content: `
        The system now uses an <strong>Instrument Intelligence Grid</strong> for rapid decision making.
        <ul>
          <li><strong>Summary Cards:</strong> A high-density view for scanning dozens of instruments. Each card highlights the Recommendation, Conviction Score, and Market Structure Phase.</li>
          <li><strong>Exhaustion Badges:</strong> Look for the ⚠️ <em>Pullback Risk</em> badge. This appears automatically when the market is overextended near resistance or support.</li>
          <li><strong>Deep-Dive View:</strong> Clicking a summary card expands the full <em>Market Intelligence Briefing</em>, revealing the chart, news sentiment, and strategic action plans.</li>
        </ul>
      `
    },
    {
      id: 'philosophy',
      title: 'Core Design Philosophy',
      icon: '🏛️',
      content: `
        This analyzer uses a <strong>Multi-Timeframe Trend Following</strong> strategy. 
        It prioritizes capital preservation and institutional-level risk management by preventing trades against the primary trend.
        <ul>
          <li><strong>Monthly Trend Foundation:</strong> We only evaluate long trades when the monthly/long-term trend is bullish (Price > 20MA > 50MA) and short trades when bearish.</li>
          <li><strong>Market Beta Filter:</strong> The engine tracks major market indices (like SPX for equities, BTC for crypto). It actively blocks buying individual assets if the broader market is collapsing.</li>
          <li><strong>Actionable Intelligence:</strong> AI generates direct "Actionable Plans" (e.g., "Wait for pullback to S1") instead of just raw data.</li>
        </ul>
      `
    },
    {
      id: 'pullback-warning',
      title: 'Pullback Warning System',
      icon: '⚠️',
      content: `
        The <strong>Exhaustion Detection Engine</strong> identifies when a trend is likely to pause or reverse <em>before</em> it happens. 
        It uses a weighted 0-8 scoring system:
        <ul>
          <li><strong>RSI Divergence (2 pts):</strong> price makes a higher high, but RSI makes a lower high (Bearish Divergence).</li>
          <li><strong>MACD Histogram Weakening (1 pt):</strong> momentum slope is declining even if price is rising.</li>
          <li><strong>ATR Compression (1 pt):</strong> volatility is squeezed, often a precursor to a sharp reversal or expansion.</li>
          <li><strong>Bollinger Re-entry (1 pt):</strong> price fails to sustain a move outside the bands and drifts back in.</li>
          <li><strong>Structure Break (3 pts):</strong> failing to make a new high and breaking a previous minor low.</li>
          <li style="color: #fab387;"><em>Signals with a score ≥ 3 trigger an immediate "Pullback Warning" and penalize the overall Conviction Score by -20 points.</em></li>
        </ul>
      `
    },
    {
      id: 'indicators',
      title: 'Logic & Scenarios',
      icon: '🧭',
      content: `
        The engine uses specific indicators tailored for different scenarios:
        <ul>
          <li><strong>ADX (Trend Strength):</strong> If ADX < 25, the market is "Chopping". The AI will downgrade setups and tell you to "Stand Aside" to avoid stop-outs.</li>
          <li><strong>Candlestick triggers:</strong> The AI scans for confirmations like <em>Bullish Engulfing</em> or <em>Hammers</em> at key support levels before entering.</li>
          <li><strong>Pivot Points & Fibonacci:</strong> Uses standard pivots (S1-R3) for normal ranges and 60-day Swing Fibonacci Extensions (1.272, 1.618) for assets in "Price Discovery" (making all-time highs).</li>
        </ul>
      `
    },
    {
      id: 'scoring',
      title: 'Score calculation Logic',
      icon: '🧮',
      content: `
        The <strong>Conviction Score</strong> runs from -100 to +100.
        <ul>
          <li><strong>Base Score:</strong> Derived from the Market Phase (Markup/Markdown/Accumulation).</li>
          <li><strong>Momentum Boosters:</strong> High ADX and rising Volume add bonus points (+15 to +25).</li>
          <li><strong>Sentiment Modifier:</strong> Real-time news intelligence impacts the final score (+/- 10 points).</li>
          <li><strong>Exhaustion Penalty:</strong> If a <em>Pullback Warning</em> is active, the score is slashed by 20 points to prevent "chasing" the move.</li>
        </ul>
      `
    },
    {
      id: 'risk',
      title: 'Position Sizing & Risk',
      icon: '🛡️',
      content: `
        Position sizing is calculated per trade based on:
        <ul>
          <li><strong>ATR-Based Volatility:</strong> Sizing is slashes on volatile assets to keep static dollar-risk.</li>
          <li><strong>Correlation Matrix:</strong> Adding Gold when you own Silver triggers a "Correlation Penalty," reducing size by up to 50% to prevent overexposure.</li>
          <li><strong>Hard Stops:</strong> Mathematically derived stops (usually 1.5x ATR) are provided for every recommendation.</li>
        </ul>
      `
    },
    {
      id: 'backtesting',
      title: 'Backtesting Methodology',
      icon: '⏱️',
      content: `
        The system validates current conditions against historical performance.
        <ul>
          <li><strong>Vectorized Simulation:</strong> Simulates the current strategy (e.g., 20MA/50MA crossover) over the last 500 days specifically for this asset.</li>
          <li><strong>Win Rate & Expectancy:</strong> Outputs the historical success rate. If an asset has a low historical win-rate for this setup, the AI will warn of "Low Confidence."</li>
        </ul>
      `
    }
  ];

  activeSection = this.sections[0].id;
}
