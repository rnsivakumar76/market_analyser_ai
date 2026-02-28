import { Component, signal, inject, OnInit } from '@angular/core';
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
      const response = await this.analyzerService.getGeopoliticalSentiment().toPromise();
      this.geopoliticalData.set(response || null);
      this.lastUpdated.set(new Date().toLocaleTimeString());
    } catch (err) {
      this.error.set('Failed to load geopolitical data');
      console.error('Geopolitical analysis error:', err);
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
  
  getCrisisAlerts() {
    const data = this.geopoliticalData();
    if (!data) return [];
    
    return [
      ...data.critical_events.map(event => ({ ...event, severity: 'CRITICAL' })),
      ...data.high_impact_events.map(event => ({ ...event, severity: 'HIGH' }))
    ].sort((a, b) => new Date(b.published).getTime() - new Date(a.published).getTime());
  }
  
  // Quick action methods
  async refreshData() {
    await this.loadGeopoliticalData();
  }
  
  async getEnergyMarketsAnalysis() {
    try {
      return await this.analyzerService.getEnergyMarketsAnalysis();
    } catch (err) {
      console.error('Energy markets analysis error:', err);
      return null;
    }
  }
  
  async getSafeHavenAnalysis() {
    try {
      return await this.analyzerService.getSafeHavenAnalysis();
    } catch (err) {
      console.error('Safe haven analysis error:', err);
      return null;
    }
  }
}
