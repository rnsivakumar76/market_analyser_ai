import { Component, signal, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MarketAnalyzerService, InstrumentAnalysis, AnalysisResponse, WeeklyPerformance, CorrelationData, StrategyMode, PsychologicalGuardrail, UserPreferences } from './services/market-analyzer.service';
import { InstrumentCardComponent } from './components/instrument-card/instrument-card.component';
import { SettingsComponent } from './components/settings/settings.component';
import { StrategySettingsComponent } from './components/strategy-settings/strategy-settings.component';
import { CorrelationModalComponent } from './components/correlation-modal/correlation-modal.component';
import { UserManualComponent } from './components/user-manual/user-manual.component';
import { LoginComponent } from './components/login/login.component';
import { AuthService, User } from './services/auth.service';
import { WatchlistHeatmapComponent } from './components/watchlist-heatmap/watchlist-heatmap.component';
import { AiCopilotComponent } from './components/ai-copilot/ai-copilot.component';
import { TradeJournalComponent } from './components/trade-journal/trade-journal.component';
import { SmartAlertsComponent } from './components/smart-alerts/smart-alerts.component';
import { GeopoliticalAnalysisComponent } from './components/geopolitical-analysis/geopolitical-analysis.component';
import { ThemeService } from './services/theme.service';
import { ThemeToggleComponent } from './components/theme-toggle/theme-toggle.component';
import { interval, Subscription, timer } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, InstrumentCardComponent, SettingsComponent, StrategySettingsComponent, CorrelationModalComponent, UserManualComponent, LoginComponent, WatchlistHeatmapComponent, AiCopilotComponent, TradeJournalComponent, SmartAlertsComponent, GeopoliticalAnalysisComponent, ThemeToggleComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
  private analyzerService = inject(MarketAnalyzerService);
  public authService = inject(AuthService);
  public themeService = inject(ThemeService);
  private analysisSub?: Subscription;

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
  showGeopoliticalAnalysis = signal(false);
  weeklyPerformance = signal<WeeklyPerformance | null>(null);
  correlationData = signal<CorrelationData | null>(null);
  psychologicalGuardrail = signal<PsychologicalGuardrail | null>(null);
  selectedInstrument = signal<InstrumentAnalysis | null>(null);
  strategyMode = signal<StrategyMode>('long_term');
  userPreferences = signal<UserPreferences | null>(null);
  prefsLoaded = signal(false);
  mobileTab = signal<'watchlist' | 'analysis' | 'context'>('watchlist');

  // Auto-refresh properties
  nextRefreshCountdown = signal<string>('05:00');
  private refreshSubscription?: Subscription;
  private countdownSubscription?: Subscription;
  private readonly REFRESH_INTERVAL_SEC = 300; // 5 minutes
  private secondsRemaining = 300;

  // Background scheduler monitoring
  private consecutiveFailures = 0;
  private readonly MAX_CONSECUTIVE_FAILURES = 2;
  private lastSuccessfulRefresh?: Date;
  private isInitialStartup = true;
  private startupTimeout?: any;
  schedulerHealthStatus = signal<'healthy' | 'warning' | 'critical' | 'initializing'>('initializing');
  schedulerHealthMessage = signal<string>('Initializing scheduler...');
  showDiagnostics = signal<boolean>(false);
  lastErrorInfo = signal<any>(null);

  ngOnInit() {
    // Load any previous error information
    this.loadLastError();
    
    // Ensure theme is initialized early
    console.log('App: ngOnInit - ensuring theme is initialized');
    this.themeService.setTheme(this.themeService.currentTheme());
    
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
      this.loadPreferences(); // runAnalysis is called inside, after mode is set
      this.startAutoRefresh();
    }
  }

  ngOnDestroy() {
    this.refreshSubscription?.unsubscribe();
    this.countdownSubscription?.unsubscribe();
    this.analysisSub?.unsubscribe();
  }

  // Fallback theme toggle methods
  fallbackThemeToggle(): void {
    console.log('App: Fallback theme toggle clicked');
    try {
      const currentTheme = this.themeService.currentTheme();
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      
      console.log('App: Switching from', currentTheme, 'to', newTheme);
      
      // Apply theme directly
      this.applyThemeDirectly(newTheme);
      
      // Update service
      this.themeService.setTheme(newTheme);
      
      console.log('App: Fallback theme changed to:', newTheme);
    } catch (error) {
      console.error('App: Error during fallback theme toggle:', error);
    }
  }

  private applyThemeDirectly(theme: 'dark' | 'light'): void {
    const root = document.documentElement;
    
    // Remove existing theme classes
    root.classList.remove('light-theme', 'dark-theme');
    
    // Add new theme class
    if (theme === 'light') {
      root.classList.add('light-theme');
    } else {
      root.classList.add('dark-theme');
    }
    
    console.log('App: Applied theme class', theme + '-theme');
    console.log('App: Root classes now:', root.className);
  }

  getFallbackThemeIcon(): string {
    const currentTheme = this.themeService.currentTheme();
    return currentTheme === 'dark' ? '🌙' : '☀️';
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
        // Set mode FIRST, then run analysis so first fetch uses the persisted mode
        this.strategyMode.set(prefs.strategy_mode || 'long_term');
        this.prefsLoaded.set(true);
        this.runAnalysis(false); // Initial load with correct persisted mode
      },
      error: () => {
        // Preferences unavailable (network error, new user) — run with default mode
        this.prefsLoaded.set(true);
        this.runAnalysis(false);
      }
    });
  }

  savePreference(key: string, value: any) {
    this.analyzerService.updatePreferences({ [key]: value }).subscribe();
  }

  toggleStrategyMode() {
    const newMode = this.strategyMode() === 'long_term' ? 'short_term' : 'long_term';
    this.switchStrategyMode(newMode);
  }

  switchStrategyMode(mode: 'long_term' | 'short_term') {
    if (this.strategyMode() === mode) return; // already in this mode
    this.strategyMode.set(mode);
    this.savePreference('strategy_mode', mode);
    this.runAnalysis(); // triggers full refetch with new mode
    this.secondsRemaining = this.REFRESH_INTERVAL_SEC; // reset countdown
  }

  refreshAnalysis() {
    this.runAnalysis(false, true);
    this.secondsRemaining = this.REFRESH_INTERVAL_SEC;
  }

  runAnalysis(silent: boolean = false, refresh: boolean = false) {
    if (this.analysisSub) {
      this.analysisSub.unsubscribe();
    }

    if (!silent) {
      this.loading.set(true);
    }
    this.error.set(null);

    this.analysisSub = this.analyzerService.analyzeAll(this.strategyMode(), refresh).subscribe({
      next: (response: AnalysisResponse) => {
        let newInstruments = [...response.instruments];

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

        // Track scheduler health
        this.handleSchedulerSuccess();
      },
      error: (err) => {
        console.error('Analysis failed:', err);
        if (!silent) {
          this.error.set('Failed to fetch analysis. Make sure the backend is running.');
        }
        this.loading.set(false);

        // Track scheduler health
        this.handleSchedulerFailure(err);
      }
    });
  }

  private handleSchedulerSuccess(): void {
    this.consecutiveFailures = 0;
    this.lastSuccessfulRefresh = new Date();
    
    if (this.isInitialStartup) {
      this.isInitialStartup = false;
      this.schedulerHealthStatus.set('healthy');
      this.schedulerHealthMessage.set('Scheduler running normally');
      console.log('App: Initial startup completed - scheduler healthy');
    } else {
      this.schedulerHealthStatus.set('healthy');
      this.schedulerHealthMessage.set('Scheduler running normally');
    }

    // Clear any startup timeout
    if (this.startupTimeout) {
      clearTimeout(this.startupTimeout);
      this.startupTimeout = undefined;
    }
  }

  private handleSchedulerFailure(error: any): void {
    this.consecutiveFailures++;
    
    console.error(`Scheduler failure #${this.consecutiveFailures}:`, error);

    // Enhanced error analysis for CloudWatch issues
    const errorMessage = this.extractErrorMessage(error);
    const isCloudWatchError = this.isCloudWatchError(error);
    const isTimeoutError = this.isTimeoutError(error);
    const isNetworkError = this.isNetworkError(error);

    // Get detailed CloudWatch analysis if applicable
    const cloudWatchAnalysis = isCloudWatchError ? this.analyzeCloudWatchError(error) : null;

    if (this.isInitialStartup) {
      this.schedulerHealthStatus.set('critical');
      
      if (cloudWatchAnalysis) {
        this.schedulerHealthMessage.set(`${cloudWatchAnalysis.service}: ${cloudWatchAnalysis.issue}`);
      } else if (isTimeoutError) {
        this.schedulerHealthMessage.set('Analysis timeout - Backend may be overloaded');
      } else if (isNetworkError) {
        this.schedulerHealthMessage.set('Network connectivity issues - Check connection');
      } else {
        this.schedulerHealthMessage.set('Initial analysis failed - Data may be stale');
      }
      
      // Set a timeout to show critical message if startup takes too long
      if (!this.startupTimeout) {
        this.startupTimeout = setTimeout(() => {
          if (this.isInitialStartup) {
            this.schedulerHealthStatus.set('critical');
            this.schedulerHealthMessage.set('Startup failed - Check backend and AWS services');
          }
        }, 10000); // 10 seconds
      }
    } else if (this.consecutiveFailures >= this.MAX_CONSECUTIVE_FAILURES) {
      this.schedulerHealthStatus.set('critical');
      
      if (cloudWatchAnalysis) {
        this.schedulerHealthMessage.set(`${cloudWatchAnalysis.service} errors (${this.consecutiveFailures}x): ${cloudWatchAnalysis.issue}`);
      } else if (isTimeoutError) {
        this.schedulerHealthMessage.set(`Analysis timeouts (${this.consecutiveFailures}x) - Backend overloaded`);
      } else if (isNetworkError) {
        this.schedulerHealthMessage.set(`Network failures (${this.consecutiveFailures}x) - Connection unstable`);
      } else {
        this.schedulerHealthMessage.set(`Scheduler failed ${this.consecutiveFailures} times - Data may be stale`);
      }
    } else if (this.consecutiveFailures === 1) {
      this.schedulerHealthStatus.set('warning');
      
      if (cloudWatchAnalysis) {
        this.schedulerHealthMessage.set(`${cloudWatchAnalysis.service} issue: ${cloudWatchAnalysis.issue}`);
      } else if (isTimeoutError) {
        this.schedulerHealthMessage.set('Analysis timeout - Retrying...');
      } else if (isNetworkError) {
        this.schedulerHealthMessage.set('Network connectivity issues');
      } else {
        this.schedulerHealthMessage.set('Scheduler experiencing issues');
      }
    }

    // Log detailed error information for debugging
    this.logDetailedError(error, this.consecutiveFailures, cloudWatchAnalysis);
  }

  private extractErrorMessage(error: any): string {
    if (typeof error === 'string') return error;
    if (error?.message) return error.message;
    if (error?.error?.message) return error.error.message;
    if (error?.statusText) return error.statusText;
    return 'Unknown error occurred';
  }

  private isCloudWatchError(error: any): boolean {
    const message = this.extractErrorMessage(error).toLowerCase();
    const cloudWatchIndicators = [
      'cloudwatch',
      'aws',
      'lambda',
      'api gateway',
      'execution timeout',
      'function timeout',
      'resource not found',
      'access denied',
      'credentials',
      'task timed out',
      'lambda timeout',
      'cold start',
      'memory limit',
      'concurrency limit',
      'throttling',
      'rate limit',
      'service unavailable',
      'internal server error',
      'bad gateway',
      'gateway timeout'
    ];
    return cloudWatchIndicators.some(indicator => message.includes(indicator));
  }

  private analyzeCloudWatchError(error: any): { service: string; issue: string; severity: 'high' | 'medium' | 'low' } {
    const message = this.extractErrorMessage(error).toLowerCase();
    
    // Lambda-specific issues
    if (message.includes('lambda') || message.includes('function timeout') || message.includes('task timed out')) {
      if (message.includes('timeout')) {
        return { service: 'AWS Lambda', issue: 'Function timeout - Analysis taking too long', severity: 'high' };
      } else if (message.includes('memory')) {
        return { service: 'AWS Lambda', issue: 'Memory limit exceeded', severity: 'high' };
      } else if (message.includes('cold start')) {
        return { service: 'AWS Lambda', issue: 'Cold start delay', severity: 'medium' };
      }
    }
    
    // API Gateway issues
    if (message.includes('api gateway') || message.includes('gateway')) {
      if (message.includes('timeout')) {
        return { service: 'API Gateway', issue: 'Gateway timeout - Backend overloaded', severity: 'high' };
      } else if (message.includes('bad gateway')) {
        return { service: 'API Gateway', issue: 'Bad gateway - Lambda not responding', severity: 'high' };
      }
    }
    
    // General AWS service issues
    if (message.includes('service unavailable') || message.includes('internal server error')) {
      return { service: 'AWS Services', issue: 'Service temporarily unavailable', severity: 'medium' };
    }
    
    // Throttling/Rate limiting
    if (message.includes('throttling') || message.includes('rate limit') || message.includes('concurrency')) {
      return { service: 'AWS Lambda', issue: 'Throttling - Too many concurrent requests', severity: 'medium' };
    }
    
    // Credentials/Permissions
    if (message.includes('access denied') || message.includes('credentials')) {
      return { service: 'AWS IAM', issue: 'Access permissions or credentials issue', severity: 'high' };
    }
    
    return { service: 'AWS', issue: 'Unknown AWS service error', severity: 'medium' };
  }

  private isTimeoutError(error: any): boolean {
    const message = this.extractErrorMessage(error).toLowerCase();
    const timeoutIndicators = [
      'timeout',
      'timed out',
      'deadline',
      'timeout exceeded',
      'connection timeout',
      'read timeout'
    ];
    return timeoutIndicators.some(indicator => message.includes(indicator));
  }

  private isNetworkError(error: any): boolean {
    const message = this.extractErrorMessage(error).toLowerCase();
    const networkIndicators = [
      'network',
      'connection',
      'fetch',
      'cors',
      'offline',
      'unreachable',
      'dns',
      'socket'
    ];
    return networkIndicators.some(indicator => message.includes(indicator));
  }

  private logDetailedError(error: any, failureCount: number, cloudWatchAnalysis?: any): void {
    const errorInfo = {
      timestamp: new Date().toISOString(),
      failureCount: failureCount,
      errorMessage: this.extractErrorMessage(error),
      errorType: this.classifyError(error),
      isCloudWatch: this.isCloudWatchError(error),
      isTimeout: this.isTimeoutError(error),
      isNetwork: this.isNetworkError(error),
      cloudWatchAnalysis: cloudWatchAnalysis,
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    console.group('🚨 Scheduler Error Analysis');
    console.error('Error Details:', errorInfo);
    console.error('Original Error:', error);
    console.groupEnd();

    // Store error info for potential debugging
    this.storeLastError(errorInfo);
  }

  private classifyError(error: any): string {
    if (this.isCloudWatchError(error)) return 'CloudWatch/AWS';
    if (this.isTimeoutError(error)) return 'Timeout';
    if (this.isNetworkError(error)) return 'Network';
    if (error?.status >= 500) return 'Server Error';
    if (error?.status >= 400) return 'Client Error';
    return 'Unknown';
  }

  private storeLastError(errorInfo: any): void {
    try {
      localStorage.setItem('lastSchedulerError', JSON.stringify(errorInfo));
      this.lastErrorInfo.set(errorInfo);
    } catch (e) {
      console.warn('Could not store error info:', e);
    }
  }

  private loadLastError(): void {
    try {
      const stored = localStorage.getItem('lastSchedulerError');
      if (stored) {
        this.lastErrorInfo.set(JSON.parse(stored));
      }
    } catch (e) {
      console.warn('Could not load error info:', e);
    }
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

  formatNewsAge(published_at?: string): string {
    if (!published_at) return '';
    try {
      const pub = new Date(published_at);
      if (isNaN(pub.getTime())) return '';
      const diffMs = Date.now() - pub.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1)   return 'just now';
      if (diffMins < 60)  return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7)   return `${diffDays}d ago`;
      return pub.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  }

  isStaleNews(published_at?: string): boolean {
    if (!published_at) return false;
    try {
      const pub = new Date(published_at);
      if (isNaN(pub.getTime())) return false;
      return (Date.now() - pub.getTime()) > 48 * 60 * 60 * 1000; // older than 48h
    } catch {
      return false;
    }
  }
}
