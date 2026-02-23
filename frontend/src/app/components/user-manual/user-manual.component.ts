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
      id: 'philosophy',
      title: 'Core Design Philosophy',
      icon: '🏛️',
      content: `
        This analyzer uses a <strong>Multi-Timeframe Trend Following</strong> strategy. 
        It prioritizes capital preservation and institutional-level risk management by preventing trades against the primary trend.
        <ul>
          <li><strong>Monthly Trend Foundation:</strong> We only evaluate long trades when the monthly/long-term trend is bullish (Price > 20MA > 50MA) and short trades when bearish.</li>
          <li><strong>Market Beta Filter:</strong> The engine tracks major market indices (like SPX for equities, BTC for crypto). It actively blocks buying individual assets if the broader market is collapsing.</li>
          <li><strong>Actionable Intelligence:</strong> Instead of just raw data, the AI generates direct, human-readable "Actionable Plans" (e.g., "Wait for pullback to S1").</li>
        </ul>
      `
    },
    {
      id: 'indicators',
      title: 'Indicators & Scenarios',
      icon: '🧭',
      content: `
        The engine uses specific indicators tailored for different market scenarios:
        <ul>
          <li><strong>RSI & ADX (Momentum & Strength):</strong> Used to confirm the validity of a breakout. If ADX is < 25, the market is chopping sideways, and the AI will downgrade the setup and tell you to "Stand Aside".</li>
          <li><strong>Candlestick Patterns (Entry Triggers):</strong> The AI scans daily candles to find exact entry triggers. Even in a strong uptrend, it requires a confirmation candle (like a Bullish Engulfing or Hammer) at a support level before generating a "Market Entry" signal.</li>
          <li><strong>Pivot Points (Intraday/Short-term Levels):</strong> Mathematical support (S1-S3) and resistance (R1-R3) ranges used to provide exact entry targets on pullbacks and immediate profit-taking zones.</li>
          <li><strong>Swing Fibonacci Ranges (Extreme Moves):</strong> When an asset breaks into "price discovery" past R3 or below S3, standard pivots stop working. The AI calculates 60-day swing Fibonacci Extensions (e.g., 1.272, 1.618) to provide logical mathematical targets even when no historical resistance exists.</li>
        </ul>
      `
    },
    {
      id: 'scoring',
      title: 'Score Calculation Logic',
      icon: '🧮',
      content: `
        The <strong>Conviction Score</strong> runs from -100 (Extreme Bearish) to +100 (Extreme Bullish). It is an aggregated penalty/reward system:
        <ul>
          <li><strong>Base Score (Trend & Phase):</strong> A strong markup phase awards significant positive points, while a distribution phase penalizes the score.</li>
          <li><strong>Momentum Boosters:</strong> High ADX (> 25) paired with rising volume and favorable RSI adds bonus points (+15 to +25).</li>
          <li><strong>Technical Breakouts:</strong> A confirmed mathematical breakout past recent resistance adds a flat momentum boost (+15 points).</li>
          <li><strong>News Sentiment:</strong> Real-time news sentiment acts as a final modifier (+10 for highly bullish news, -10 for highly bearish news within the last 24 hours).</li>
          <li><em>Only assets scoring > 60 (or < -60 for shorts) and passing the ADX/Beta hard filters are marked as "Trade-Worthy".</em></li>
        </ul>
      `
    },
    {
      id: 'risk',
      title: 'Dynamic Position Sizing & Risk',
      icon: '🛡️',
      content: `
        Our AI calculates the exact amount of capital to deploy based on active market conditions.
        <ul>
          <li><strong>Volatility-Adjusted Units:</strong> Position size is dynamically downsized for highly volatile assets (using ATR) to keep your actual dollar-risk identical across different trades.</li>
          <li><strong>Correlation Penalty:</strong> If you add highly correlated assets (like grabbing Gold while already holding Silver), the AI detects the correlation matrix and automatically slashes the recommended position size by up to 50% to prevent portfolio overexposure.</li>
          <li><strong>Hard Stops:</strong> Every recommendation comes with a mathematically derived Stop Loss to protect your capital.</li>
        </ul>
      `
    },
    {
      id: 'backtesting',
      title: 'Backtesting Methodology',
      icon: '⏱️',
      content: `
        The system continuously validates current conditions against historical performance to gauge reliability.
        <ul>
          <li><strong>Vectorized Historical Simulation:</strong> The engine rapidly simulates buying the asset under the exact same moving average (20MA/50MA crossover) conditions over the last 500 days.</li>
          <li><strong>Win Rate & Expectancy:</strong> It outputs the historical Win Rate and Expected Return of the current setup. A low historical win-rate will warn you that this specific asset frequently fails technical breakouts.</li>
          <li><strong>Max Drawdown:</strong> Highlights the worst historical pain experienced under these conditions, helping set realistic expectations for holding through volatility.</li>
        </ul>
      `
    }
  ];

  activeSection = this.sections[0].id;
}
