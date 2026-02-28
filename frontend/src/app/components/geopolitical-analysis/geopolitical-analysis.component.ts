import { Component, signal, inject, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MarketAnalyzerService, GeopoliticalData, GeopoliticalEvent, TradingRecommendation } from '../../services/market-analyzer.service';

@Component({
  selector: 'app-geopolitical-analysis',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './geopolitical-analysis.component.html',
  styleUrls: ['./geopolitical-analysis.component.scss']
})
export class GeopoliticalAnalysisComponent implements OnInit {
  private analyzerService = inject(MarketAnalyzerService);
  
  @Output() close = new EventEmitter<void>();
  
  geopoliticalData = signal<GeopoliticalData | null>(null);
  loading = signal(false);
  error = signal<string | null>(null);
  lastUpdated = signal<string | null>(null);
  
  // Auto-refresh settings
  autoRefresh = signal(true);
  refreshInterval: any = null;
  
  ngOnInit() {
    this.loadGeopoliticalData();
    this.startAutoRefresh();
  }
  
  ngOnDestroy() {
    this.stopAutoRefresh();
  }
  
  async loadGeopoliticalData() {
    this.loading.set(true);
    this.error.set(null);
    
    try {
      console.log('Loading geopolitical data...');
      const response = await this.analyzerService.getGeopoliticalSentiment().toPromise();
      console.log('Geopolitical data received:', response);
      this.geopoliticalData.set(response || null);
      this.lastUpdated.set(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Geopolitical analysis error:', err);
      this.error.set('Failed to load geopolitical data');
    } finally {
      this.loading.set(false);
    }
  }
  
  startAutoRefresh() {
    if (this.autoRefresh()) {
      this.refreshInterval = setInterval(() => {
        this.loadGeopoliticalData();
      }, 5 * 60 * 1000); // Refresh every 5 minutes
    }
  }
  
  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }
  
  toggleAutoRefresh() {
    this.autoRefresh.set(!this.autoRefresh());
    if (this.autoRefresh()) {
      this.startAutoRefresh();
    } else {
      this.stopAutoRefresh();
    }
  }
  
  // Helper methods for UI
  getSentimentColor(score: number): string {
    if (score > 0.2) return 'positive';
    if (score < -0.2) return 'negative';
    return 'neutral';
  }
  
  getRiskLevelColor(level: string): string {
    switch (level) {
      case 'CRITICAL': return 'critical';
      case 'HIGH': return 'high';
      case 'MODERATE': return 'moderate';
      case 'LOW': return 'low';
      default: return 'unknown';
    }
  }
  
  getActionColor(action: string): string {
    switch (action) {
      case 'BUY': return 'buy';
      case 'SELL': return 'sell';
      case 'HOLD': return 'hold';
      default: return 'neutral';
    }
  }
  
  getConfidenceColor(confidence: number): string {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
  }
  
  formatTime(published: string): string {
    const date = new Date(published);
    const now = new Date();
    const hours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }
  
  // Specific analysis methods
  getEnergyMarketsData() {
    const data = this.geopoliticalData();
    if (!data) return null;
    
    return {
      recommendations: data.trading_recommendations.energy_markets,
      sentiment: data.overall_sentiment.overall_score,
      outlook: data.affected_sectors['energy'] || 0
    };
  }
  
  getSafeHavenData() {
    const data = this.geopoliticalData();
    if (!data) return null;
    
    return {
      recommendations: data.trading_recommendations.commodities,
      sentiment: data.overall_sentiment.overall_score,
      outlook: data.affected_sectors['commodities'] || 0
    };
  }
  
  getSectorList(): string[] {
    const data = this.geopoliticalData();
    if (!data || !data.affected_sectors) {
      return [];
    }
    return Object.keys(data.affected_sectors);
  }

  getCrisisAlerts() {
    const data = this.geopoliticalData();
    if (!data) return [];
    
    return [
      ...data.critical_events.map(event => ({
        severity: 'CRITICAL',
        title: event.title,
        description: event.description,
        source: event.source,
        published: event.published,
        affected_sectors: event.affected_sectors,
        conflict_keywords: event.conflict_keywords
      })),
      ...data.high_impact_events.map(event => ({
        severity: 'HIGH',
        title: event.title,
        description: event.description,
        source: event.source,
        published: event.published,
        affected_sectors: event.affected_sectors,
        conflict_keywords: event.conflict_keywords
      }))
    ].sort((a, b) => new Date(b.published).getTime() - new Date(a.published).getTime());
  }
  
  // Quick action methods
  async refreshData() {
    console.log('Refresh button clicked');
    await this.loadGeopoliticalData();
  }
  
  async getEnergyMarketsAnalysis() {
    console.log('Energy markets analysis requested');
    try {
      return await this.analyzerService.getEnergyMarketsAnalysis();
    } catch (err) {
      console.error('Energy markets analysis error:', err);
      return null;
    }
  }
  
  async getSafeHavenAnalysis() {
    console.log('Safe haven analysis requested');
    try {
      return await this.analyzerService.getSafeHavenAnalysis();
    } catch (err) {
      console.error('Safe haven analysis error:', err);
      return null;
    }
  }
}
