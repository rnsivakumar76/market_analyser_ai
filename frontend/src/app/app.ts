import { Component, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MarketAnalyzerService, InstrumentAnalysis, AnalysisResponse } from './services/market-analyzer.service';
import { InstrumentCardComponent } from './components/instrument-card/instrument-card.component';
import { SettingsComponent } from './components/settings/settings.component';
import { PerformanceBannerComponent } from './components/performance-banner/performance-banner.component';
import { StrategySettingsComponent } from './components/strategy-settings/strategy-settings.component';
import { CorrelationHeatmapComponent } from './components/correlation-heatmap/correlation-heatmap.component';
import { CorrelationModalComponent } from './components/correlation-modal/correlation-modal.component';
import { WeeklyPerformance, CorrelationData } from './services/market-analyzer.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, InstrumentCardComponent, SettingsComponent, PerformanceBannerComponent, StrategySettingsComponent, CorrelationHeatmapComponent, CorrelationModalComponent], templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  private analyzerService = inject(MarketAnalyzerService);

  instruments = signal<InstrumentAnalysis[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);
  lastUpdated = signal<string | null>(null);
  showSettings = signal(false);
  showStrategySettings = signal(false);
  showCorrelationModal = signal(false);
  weeklyPerformance = signal<WeeklyPerformance | null>(null);
  correlationData = signal<CorrelationData | null>(null);

  ngOnInit() {
    this.runAnalysis();
  }

  runAnalysis() {
    this.loading.set(true);
    this.error.set(null);

    this.analyzerService.analyzeAll().subscribe({
      next: (response: AnalysisResponse) => {
        this.instruments.set(response.instruments);
        this.weeklyPerformance.set(response.weekly_performance);
        this.correlationData.set(response.correlation_data);
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
