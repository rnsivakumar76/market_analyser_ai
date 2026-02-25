import { Component, signal, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MarketAnalyzerService, InstrumentAnalysis, AnalysisResponse, WeeklyPerformance, CorrelationData, StrategyMode, PsychologicalGuardrail, UserPreferences } from './services/market-analyzer.service';
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
import { TradeJournalComponent } from './components/trade-journal/trade-journal.component';
import { SmartAlertsComponent } from './components/smart-alerts/smart-alerts.component';
import { interval, Subscription, timer } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, InstrumentCardComponent, InstrumentSummaryComponent, SettingsComponent, PerformanceBannerComponent, StrategySettingsComponent, CorrelationModalComponent, UserManualComponent, LoginComponent, WatchlistHeatmapComponent, AiCopilotComponent, MultiTimeframeOverlayComponent, TradeJournalComponent, SmartAlertsComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
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
  showTradeJournal = signal(false);
  showSmartAlerts = signal(false);
  weeklyPerformance = signal<WeeklyPerformance | null>(null);
  correlationData = signal<CorrelationData | null>(null);
  psychologicalGuardrail = signal<PsychologicalGuardrail | null>(null);
  selectedInstrument = signal<InstrumentAnalysis | null>(null);
  strategyMode = signal<StrategyMode>('long_term');
  userPreferences = signal<UserPreferences | null>(null);
  prefsLoaded = signal(false);

  // Auto-refresh properties
  nextRefreshCountdown = signal<string>('05:00');
  private refreshSubscription?: Subscription;
  private countdownSubscription?: Subscription;
  private readonly REFRESH_INTERVAL_SEC = 300; // 5 minutes
  private secondsRemaining = 300;

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
      this.loadPreferences();
      this.runAnalysis(false); // Initial load: not silent, show loading screen
      this.startAutoRefresh();
    }
  }

  ngOnDestroy() {
    this.refreshSubscription?.unsubscribe();
    this.countdownSubscription?.unsubscribe();
  }

  private startAutoRefresh() {
    // 1. Scheduler for Analysis
    this.refreshSubscription = interval(this.REFRESH_INTERVAL_SEC * 1000).subscribe(() => {
      this.runAnalysis(true); // Background update: silent
      this.secondsRemaining = this.REFRESH_INTERVAL_SEC;
    });

    // 2. Scheduler for Countdown Timer
    this.countdownSubscription = interval(1000).subscribe(() => {
      if (this.secondsRemaining > 0) {
        this.secondsRemaining--;
      }
      const mins = Math.floor(this.secondsRemaining / 60);
      const secs = this.secondsRemaining % 60;
      this.nextRefreshCountdown.set(`${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`);
    });
  }

  loadPreferences() {
    this.analyzerService.getPreferences().subscribe({
      next: (prefs) => {
        this.userPreferences.set(prefs);
        this.strategyMode.set(prefs.strategy_mode || 'long_term');
        this.prefsLoaded.set(true);
      },
      error: () => { this.prefsLoaded.set(true); }
    });
  }

  savePreference(key: string, value: any) {
    this.analyzerService.updatePreferences({ [key]: value }).subscribe();
  }

  toggleStrategyMode() {
    const newMode = this.strategyMode() === 'long_term' ? 'short_term' : 'long_term';
    this.strategyMode.set(newMode);
    this.savePreference('strategy_mode', newMode);
    this.runAnalysis();
    this.secondsRemaining = this.REFRESH_INTERVAL_SEC; // Reset countdown on manual toggle
  }


  runAnalysis(silent: boolean = false) {
    if (!silent) {
      this.loading.set(true);
    }
    this.error.set(null);

    this.analyzerService.analyzeAll(this.strategyMode()).subscribe({
      next: (response: AnalysisResponse) => {
        const currentInstruments = this.instruments();
        let newInstruments = [...response.instruments];

        // Merge logic: If background update misses some instruments (e.g. API fail), 
        // keep the old data instead of blanking out.
        if (currentInstruments.length > 0) {
          const newSymbols = new Set(newInstruments.map(i => i.symbol));
          const missingFromNew = currentInstruments.filter(i => !newSymbols.has(i.symbol));

          // Only keep missing instruments if the response wasn't totally empty 
          // (which might mean a global error or zero instruments configured)
          if (newInstruments.length > 0) {
            newInstruments = [...newInstruments, ...missingFromNew];
          }
        }

        // Sort instruments: Highest magnitude score at the top
        const sortedInstruments = newInstruments.sort((a, b) => {
          return Math.abs(b.trade_signal.score) - Math.abs(a.trade_signal.score);
        });

        this.instruments.set(sortedInstruments);

        // Update selection if exists
        const currentSelection = this.selectedInstrument();
        if (currentSelection) {
          const updated = sortedInstruments.find(i => i.symbol === currentSelection.symbol);
          if (updated) {
            this.selectedInstrument.set(updated);
          }
          // If updated is null, we keep the previous selectedInstrument 
          // so the screen doesn't go blank.
        }

        this.weeklyPerformance.set(response.weekly_performance);
        this.correlationData.set(response.correlation_data);
        this.psychologicalGuardrail.set(response.psychological_guardrail);
        this.lastUpdated.set(new Date(response.analysis_timestamp).toLocaleString());
        this.loading.set(false);
      },
      error: (err) => {
        if (!silent) {
          this.error.set('Failed to fetch analysis. Make sure the backend is running.');
        }
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
