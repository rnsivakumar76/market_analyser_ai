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
      id: 'strategy-modes',
      title: 'Strategy & Timeframes',
      icon: '⏱️',
      content: `
        You can now toggle between <strong>Long Term</strong> and <strong>Short Term</strong> operational modes using the toggle next to the Refresh button.
        <ul>
          <li><strong>Long Term (Swing/Position):</strong> Analyzes the Monthly trend, Weekly pullbacks, and Daily execution. Best for building portfolios over months.</li>
          <li><strong>Short Term (Day/Swing):</strong> Analyzes the Daily trend, 4-Hour pullbacks, and 1-Hour execution. Best for capturing moves over days.</li>
          <li><em>Switching modes will trigger a complete re-analysis of your watchlist across the new timeframes.</em></li>
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
      id: 'pro-tools',
      title: 'Institutional Alpha & Scaling',
      icon: '🚀',
      content: `
        Professional setups require more than just a chart. These tools separate the "retail" behavior from "institutional" systems.
        <ul>
          <li><strong>The Alpha Shield (Relative Strength):</strong> Compares the asset directly against its benchmark (SPX for stocks, BTC for crypto). 
              The system <strong>actively blocks</strong> long trades on instruments that are underperforming the market (laggards). We only buy the strongest horses.</li>
          <li><strong>Multi-Stage Scaling (TP1, TP2, TP3):</strong> Institutional traders rarely exit all at once.
              <ul>
                <li><em>Stage 1 (De-risk):</em> Take 30% profit at 1.0x ATR and move SL to break-even.</li>
                <li><em>Stage 2 (Bank Profit):</em> Take 40% at 2.0x ATR.</li>
                <li><em>Stage 3 (Runner):</em> Leave 30% to capture massive trends, trailing with a 2.0x ATR buffer.</li>
              </ul>
          </li>
          <li><strong>The Macro Event Guard:</strong> Automatically scans the global economic calendar and corporate earnings. 
              If a high-impact event (NFP, CPI, FOMC) occurs within 48h, the <strong>Macro Shield</strong> blocks the trade to prevent "gap" risk.</li>
        </ul>
      `
    },
    {
      id: 'terminology',
      title: 'Trading Terminology Guide',
      icon: '📚',
      content: `
        <h4>Technical Indicators & Terms</h4>
        <div class="term-section">
          <strong>ADX (Average Directional Index)</strong>
          <p>Measures trend strength on a scale of 0-100. Values above 25 indicate a trending market, while below 25 suggests ranging/choppy conditions. ADX is non-directional - it only shows strength, not direction.</p>
        </div>
        
        <div class="term-section">
          <strong>RSI (Relative Strength Index)</strong>
          <p>Momentum oscillator that measures the speed and change of price movements on a scale of 0-100. Readings above 70 suggest overbought conditions, below 30 suggest oversold conditions. Used to identify potential reversals.</p>
        </div>
        
        <div class="term-section">
          <strong>ATR (Average True Range)</strong>
          <p>Measures market volatility by calculating the average range between high and low prices over a set period. Used for position sizing and stop-loss placement. Higher ATR = higher volatility.</p>
        </div>
        
        <div class="term-section">
          <strong>MACD (Moving Average Convergence Divergence)</strong>
          <p>Trend-following momentum indicator showing the relationship between two moving averages of an asset's price. The histogram shows the distance between MACD and signal line, indicating momentum strength.</p>
        </div>
        
        <div class="term-section">
          <strong>Bollinger Bands</strong>
          <p>Volatility indicator consisting of a middle band (simple moving average) and two outer bands set at 2 standard deviations. Bands widen during high volatility and narrow during low volatility.</p>
        </div>
        
        <h4>Market Structure & Patterns</h4>
        <div class="term-section">
          <strong>Pullback</strong>
          <p>A temporary reversal in the overall trend. In an uptrend, it's a downward movement before the price resumes its upward move. Pullbacks provide better entry opportunities than chasing breakouts.</p>
        </div>
        
        <div class="term-section">
          <strong>Support & Resistance</strong>
          <p>Support: Price level where buying pressure overcomes selling pressure, preventing further price decline.<br>
          Resistance: Price level where selling pressure overcomes buying pressure, preventing further price increase.</p>
        </div>
        
        <div class="term-section">
          <strong>Pivot Points</strong>
          <p>Technical analysis indicator that determines potential support and resistance levels based on previous day's high, low, and close prices. Key levels: S1, S2 (support), R1, R2 (resistance), and main pivot.</p>
        </div>
        
        <div class="term-section">
          <strong>Fibonacci Retracements</strong>
          <p>Horizontal lines that indicate where support and resistance are likely to occur based on Fibonacci ratios (23.6%, 38.2%, 50%, 61.8%). Used to identify potential reversal levels after price movements.</p>
        </div>
        
        <h4>Volume & Liquidity</h4>
        <div class="term-section">
          <strong>Volume Profile</strong>
          <p>Shows the amount of volume traded at specific price levels over a period. Key levels include POC (Point of Control - highest volume), VAH (Value Area High), and VAL (Value Area Low).</p>
        </div>
        
        <div class="term-section">
          <strong>VWAP (Volume Weighted Average Price)</strong>
          <p>Trading benchmark that gives the average price an asset has traded at throughout the day, based on both volume and price. Used by institutions to assess entry/exit quality.</p>
        </div>
        
        <div class="term-section">
          <strong>Liquidity</strong>
          <p>The degree to which an asset can be quickly bought or sold without affecting its price. High liquidity means tight spreads and stable prices, low liquidity means wide spreads and volatile prices.</p>
        </div>
        
        <h4>Risk Management Metrics</h4>
        <div class="term-section">
          <strong>Sharpe Ratio</strong>
          <p>Measures risk-adjusted return. Higher values indicate better returns for the risk taken. Ratio > 1 is considered good, > 2 is very good.</p>
        </div>
        
        <div class="term-section">
          <strong>Maximum Drawdown</strong>
          <p>The maximum observed loss from a peak to a trough of a portfolio before a new peak is attained. Measures the largest potential loss in a given period.</p>
        </div>
        
        <div class="term-section">
          <strong>MAE (Maximum Adverse Excursion)</strong>
          <p>The maximum loss experienced during a trade before it either hits the target or stop loss. Helps assess typical risk exposure in winning trades.</p>
        </div>
        
        <div class="term-section">
          <strong>Expectancy</strong>
          <p>The average amount expected to be won or lost per trade. Formula: (Win Rate × Average Win) - (Loss Rate × Average Loss). Positive expectancy indicates a profitable strategy.</p>
        </div>
        
        <h4>Market Correlation</h4>
        <div class="term-section">
          <strong>Beta</strong>
          <p>Measures an asset's volatility in relation to the overall market. Beta > 1 means more volatile than market, < 1 means less volatile.</p>
        </div>
        
        <div class="term-section">
          <strong>Correlation Coefficient</strong>
          <p>Statistical measure ranging from -1 to +1 indicating how two assets move in relation to each other. +1 means perfect positive correlation, -1 means perfect negative correlation, 0 means no correlation.</p>
        </div>
        
        <h4>Trading Sessions</h4>
        <div class="term-section">
          <strong>Session VWAP</strong>
          <p>VWAP calculated for specific trading sessions (Asia, London, New York). Helps identify intraday support/resistance and assess price performance relative to each session's average.</p>
        </div>
        
        <div class="term-section">
          <strong>Stop Hunt</strong>
          <p>Price action that moves rapidly to key levels where stop-loss orders are clustered, triggering those stops before reversing in the original direction. Common at round numbers and key technical levels.</p>
        </div>
        
        <h4>Strategy Terms</h4>
        <div class="term-section">
          <strong>Multi-Timeframe Analysis</strong>
          <p>Analyzing an asset across different timeframes (monthly, weekly, daily, hourly) to get a comprehensive view of the trend and identify optimal entry/exit points.</p>
        </div>
        
        <div class="term-section">
          <strong>Risk-Reward Ratio</strong>
          <p>The ratio of potential profit to potential loss on a trade. A 1:2 ratio means risking $1 to potentially make $2. Higher ratios are generally preferred.</p>
        </div>
        
        <div class="term-section">
          <strong>Position Sizing</strong>
          <p>Determining the appropriate number of shares/contracts to trade based on account size, risk tolerance, and volatility. Critical for proper risk management.</p>
        </div>
        
        <div class="term-section">
          <strong>Breakout</strong>
          <p>When price moves above a resistance level or below a support level with increased volume, suggesting the start of a new trend.</p>
        </div>
        
        <div class="term-section">
          <strong>Fakeout</strong>
          <p>A false breakout where price moves beyond a key level but quickly reverses back, trapping traders who entered on the breakout.</p>
        </div>
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
