import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MarketAnalyzerService, InstrumentAnalysis, AnalysisResponse, WeeklyPerformance, CorrelationData, StrategyMode, PsychologicalGuardrail } from './services/market-analyzer.service';
import { InstrumentCardComponent } from './components/instrument-card/instrument-card.component';
import { SettingsComponent } from './components/settings/settings.component';
import { PerformanceBannerComponent } from './components/performance-banner/performance-banner.component';
import { StrategySettingsComponent } from './components/strategy-settings/strategy-settings.component';
import { CorrelationModalComponent } from './components/correlation-modal/correlation-modal.component';
import { UserManualComponent } from './components/user-manual/user-manual.component';
import { LoginComponent } from './components/login/login.component';
import { AuthService, User } from './services/auth.service';
import { InstrumentSummaryComponent } from './components/instrument-summary/instrument-summary.component';
import { WatchlistHeatmapComponent } from './components/watchlist-heatmap/watchlist-heatmap.component';
import { AiCopilotComponent } from './components/ai-copilot/ai-copilot.component';
import { MultiTimeframeOverlayComponent } from './components/multi-timeframe-overlay/multi-timeframe-overlay.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, InstrumentCardComponent, InstrumentSummaryComponent, SettingsComponent, PerformanceBannerComponent, StrategySettingsComponent, CorrelationModalComponent, UserManualComponent, LoginComponent, WatchlistHeatmapComponent, AiCopilotComponent, MultiTimeframeOverlayComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  private analyzerService = inject(MarketAnalyzerService);
  public authService = inject(AuthService);

  instruments = signal<InstrumentAnalysis[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);
  lastUpdated = signal<string | null>(null);
  showSettings = signal(false);
  showStrategySettings = signal(false);
  showCorrelationModal = signal(false);
  showUserManual = signal(false);
  weeklyPerformance = signal<WeeklyPerformance | null>(null);
  correlationData = signal<CorrelationData | null>(null);
  psychologicalGuardrail = signal<PsychologicalGuardrail | null>(null);
  selectedInstrument = signal<InstrumentAnalysis | null>(null);
  strategyMode = signal<StrategyMode>('long_term');
  sidebarView = signal<'list' | 'heatmap'>('heatmap');

  ngOnInit() {
    // Check for auth token in URL (from Google callback)
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (token) {
      const user: User = {
        id: urlParams.get('id') || '',
        name: urlParams.get('name') || '',
        email: urlParams.get('email') || '',
        picture: urlParams.get('picture') || ''
      };

      this.authService.setToken(token);
      this.authService.setUser(user);

      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (this.authService.isLoggedIn) {
      this.runAnalysis();
    }
  }

  toggleStrategyMode() {
    this.strategyMode.set(this.strategyMode() === 'long_term' ? 'short_term' : 'long_term');
    this.runAnalysis();
  }

  runAnalysis() {
    this.loading.set(true);
    this.error.set(null);

    this.analyzerService.analyzeAll(this.strategyMode()).subscribe({
      next: (response: AnalysisResponse) => {
        // Sort instruments: Highest magnitude score at the top (Absolute value)
        const sortedInstruments = [...response.instruments].sort((a, b) => {
          return Math.abs(b.trade_signal.score) - Math.abs(a.trade_signal.score);
        });

        this.instruments.set(sortedInstruments);

        // Update selection if exists
        const currentSelection = this.selectedInstrument();
        if (currentSelection) {
          const updated = sortedInstruments.find(i => i.symbol === currentSelection.symbol);
          this.selectedInstrument.set(updated || null);
        }

        this.weeklyPerformance.set(response.weekly_performance);
        this.correlationData.set(response.correlation_data);
        this.psychologicalGuardrail.set(response.psychological_guardrail);
        this.lastUpdated.set(new Date(response.analysis_timestamp).toLocaleString());
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set('Failed to fetch analysis. Make sure the backend is running.');
        this.loading.set(false);
        console.error('Analysis error:', err);
      }
    });
  }

  refreshInstrument(symbol: string) {
    this.loading.set(true);
    this.analyzerService.analyzeSingle(symbol, this.strategyMode()).subscribe({
      next: (updatedAnalysis) => {
        const sortedInstruments = this.instruments().map(i => i.symbol === symbol ? updatedAnalysis : i).sort((a, b) => {
          return Math.abs(b.trade_signal.score) - Math.abs(a.trade_signal.score);
        });
        this.instruments.set(sortedInstruments);

        if (this.selectedInstrument()?.symbol === symbol) {
          this.selectedInstrument.set(updatedAnalysis);
        }
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(`Failed to refresh ${symbol}.`);
        this.loading.set(false);
        console.error('Refresh error:', err);
      }
    });
  }

  get tradeWorthyCount(): number {
    return this.instruments().filter(i => i.trade_signal.trade_worthy).length;
  }

  get bullishCount(): number {
    return this.instruments().filter(i => i.trade_signal.recommendation === 'bullish').length;
  }

  get bearishCount(): number {
    return this.instruments().filter(i => i.trade_signal.recommendation === 'bearish').length;
  }
}
