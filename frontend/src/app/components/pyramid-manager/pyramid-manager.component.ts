import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

interface PyramidPosition {
  id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  initial_lots: number;
  current_lots: number;
  current_stop_loss: number;
  current_price: number;
  unrealized_pnl: number;
  created_at: string;
  updated_at: string;
  pyramid_level: number;
  status: string;
}

interface PyramidLevel {
  level: number;
  price_target: number;
  lots_to_add: number;
  cumulative_lots: number;
  stop_loss_adjustment: number;
  description: string;
}

interface PyramidPlan {
  position_id: string;
  symbol: string;
  direction: string;
  current_level: number;
  max_levels: number;
  levels: PyramidLevel[];
  current_recommendation: any;
  total_risk: number;
  total_reward: number;
  overall_risk_reward: number;
}

interface PyramidOpportunity {
  symbol: string;
  name: string;
  direction: string;
  current_price: number;
  original_price: number;
  price_offset: number;
  entry_range: { low: number; high: number };
  stop_loss: number;
  target_profit_range: { low: number; high: number } | null;
  confidence: number;
  divergence_sources: string[];
  pyramid_plan: {
    levels: PyramidLevel[];
    total_risk: number;
    total_reward: number;
    risk_reward: number;
  };
  multi_timeframe: any;
  risk_level: string;
  trading_style: string;
}

@Component({
  selector: 'app-pyramid-manager',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pyramid-manager.component.html',
  styleUrls: ['./pyramid-manager.component.scss']
})
export class PyramidManagerComponent implements OnInit {
  @Output() back = new EventEmitter<void>();

  positions: PyramidPosition[] = [];
  historyPositions: PyramidPosition[] = [];
  selectedPosition: PyramidPosition | null = null;
  pyramidPlan: PyramidPlan | null = null;
  opportunities: PyramidOpportunity[] = [];
  showOpportunities = true;
  showHistory = false;
  
  // New position form
  newPosition = {
    symbol: '',
    direction: 'long',
    entry_price: 0,
    initial_lots: 1,
    stop_loss: 0
  };
  
  // Available instruments
  instruments = ['XAU', 'XAG', 'WTI', 'BTC'];

  // Trading style: swing (longer timeframe) or day (faster completion)
  tradingStyle = 'swing';

  isLoading = false;
  showNewPositionForm = false;
  
  constructor(private http: HttpClient) {}

  backToOverview() {
    this.back.emit();
  }

  editPosition(position: PyramidPosition) {
    // Populate form with position data for editing
    this.newPosition = {
      symbol: position.symbol,
      direction: position.direction,
      entry_price: position.entry_price,
      initial_lots: position.initial_lots,
      stop_loss: position.current_stop_loss
    };
    this.showNewPositionForm = true;
  }

  softDeletePosition(position: PyramidPosition) {
    if (confirm(`Move ${position.symbol} to history?`)) {
      console.log('Soft deleting position:', position.id);
      this.http.delete(`/api/pyramid/position/${position.id}?action=soft`).subscribe({
        next: (response) => {
          console.log('Soft delete successful:', response);
          this.loadPositions();
          this.loadHistory();
          alert('Position moved to history');
        },
        error: (error) => {
          console.error('Error soft deleting position:', error);
          alert('Failed to move to history: ' + error.message);
        }
      });
    }
  }

  hardDeletePosition(position: PyramidPosition) {
    if (confirm(`Permanently delete ${position.symbol}? This cannot be undone.`)) {
      console.log('Hard deleting position:', position.id);
      this.http.delete(`/api/pyramid/position/${position.id}?action=hard`).subscribe({
        next: (response) => {
          console.log('Hard delete successful:', response);
          this.loadPositions();
          this.loadHistory();
          alert('Position permanently deleted');
        },
        error: (error) => {
          console.error('Error hard deleting position:', error);
          alert('Failed to delete: ' + error.message);
        }
      });
    }
  }

  loadHistory() {
    this.http.get<any>('/api/pyramid/positions/history').subscribe({
      next: (response) => {
        this.historyPositions = response.positions || [];
      },
      error: (error) => console.error('Error loading history:', error)
    });
  }

  restorePosition(position: PyramidPosition) {
    // Restore by updating status back to active
    this.http.put(`/api/pyramid/position/${position.id}`, { status: 'active' }).subscribe({
      next: () => {
        this.loadPositions();
        this.loadHistory();
      },
      error: (error) => console.error('Error restoring position:', error)
    });
  }

  formatDate(dateString: string): string {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
  }

  onTradingStyleChange() {
    console.log('Trading style changed to:', this.tradingStyle);
    // Reload pyramid plan if a position is selected
    if (this.selectedPosition) {
      this.loadPyramidPlan(this.selectedPosition.id);
    }
  }

  ngOnInit() {
    this.loadPositions();
    this.loadOpportunities();
  }
  
  loadOpportunities() {
    this.isLoading = true;
    this.http.get<any>('/api/pyramid/opportunities').subscribe({
      next: (response) => {
        this.opportunities = response.opportunities || [];
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading opportunities:', error);
        this.isLoading = false;
      }
    });
  }
  
  loadPositions() {
    this.isLoading = true;
    this.http.get<any>('/api/pyramid/positions').subscribe({
      next: (response) => {
        this.positions = response.positions || [];
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading positions:', error);
        this.isLoading = false;
      }
    });
  }
  
  selectPosition(position: PyramidPosition) {
    console.log('Selecting position:', position);
    this.selectedPosition = position;
    this.loadPyramidPlan(position.id);
  }

  loadPyramidPlan(positionId: string) {
    console.log('Loading pyramid plan for:', positionId, 'with trading style:', this.tradingStyle);
    this.isLoading = true;
    this.http.get<PyramidPlan>(`/api/pyramid/position/${positionId}/plan?trading_style=${this.tradingStyle}`).subscribe({
      next: (plan) => {
        console.log('Pyramid plan loaded:', plan);
        this.pyramidPlan = plan;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading pyramid plan:', error);
        this.isLoading = false;
        alert('Failed to load pyramid plan: ' + error.message);
      }
    });
  }
  
  createPosition() {
    this.isLoading = true;
    this.http.post<any>('/api/pyramid/position', this.newPosition).subscribe({
      next: (response) => {
        this.showNewPositionForm = false;
        this.newPosition = {
          symbol: '',
          direction: 'long',
          entry_price: 0,
          initial_lots: 1,
          stop_loss: 0
        };
        this.loadPositions();
      },
      error: (error) => {
        console.error('Error creating position:', error);
        this.isLoading = false;
      }
    });
  }
  
  updatePosition(updateData: any) {
    if (!this.selectedPosition) return;
    
    this.isLoading = true;
    this.http.put<any>(`/api/pyramid/position/${this.selectedPosition.id}`, updateData).subscribe({
      next: (response) => {
        this.loadPositions();
        if (this.selectedPosition) {
          this.loadPyramidPlan(this.selectedPosition.id);
        }
      },
      error: (error) => {
        console.error('Error updating position:', error);
        this.isLoading = false;
      }
    });
  }
  
  closePosition() {
    if (!this.selectedPosition) return;
    
    if (confirm('Are you sure you want to close this position?')) {
      this.isLoading = true;
      this.http.delete<any>(`/api/pyramid/position/${this.selectedPosition.id}`).subscribe({
        next: (response) => {
          this.selectedPosition = null;
          this.pyramidPlan = null;
          this.loadPositions();
        },
        error: (error) => {
          console.error('Error closing position:', error);
          this.isLoading = false;
        }
      });
    }
  }
  
  executeRecommendation() {
    if (!this.pyramidPlan || !this.selectedPosition) return;
    
    const rec = this.pyramidPlan.current_recommendation;
    const updateData: any = {};
    
    if (rec.action === 'ADD_POSITION' && rec.target_add_lots) {
      updateData.current_lots = this.selectedPosition.current_lots + rec.target_add_lots;
      updateData.pyramid_level = this.pyramidPlan.current_level + 1;
    }
    
    if (rec.action === 'MOVE_STOP' && rec.new_stop_loss) {
      updateData.current_stop_loss = rec.new_stop_loss;
    }
    
    if (rec.action === 'PARTIAL_EXIT') {
      updateData.current_lots = Math.floor(this.selectedPosition.current_lots * 0.5);
      updateData.status = 'partial_exit';
    }
    
    if (Object.keys(updateData).length > 0) {
      this.updatePosition(updateData);
    }
  }
  
  getLevelStatus(level: number): string {
    if (!this.pyramidPlan) return 'future';
    if (level < this.pyramidPlan.current_level) return 'completed';
    if (level === this.pyramidPlan.current_level) return 'current';
    return 'future';
  }
  
  getDirectionColor(): string {
    return this.selectedPosition?.direction === 'long' ? '#10b981' : '#ef4444';
  }
  
  formatPrice(price: number): string {
    return price.toFixed(2);
  }
  
  formatPnl(pnl: number): string {
    const sign = pnl >= 0 ? '+' : '';
    return `${sign}$${pnl.toFixed(2)}`;
  }
  
  getPnlColor(): string {
    if (!this.selectedPosition) return '#64748b';
    return this.selectedPosition.unrealized_pnl >= 0 ? '#10b981' : '#ef4444';
  }
  
  createPositionFromOpportunity(opportunity: PyramidOpportunity) {
    this.newPosition = {
      symbol: opportunity.symbol,
      direction: opportunity.direction,
      entry_price: opportunity.current_price,
      initial_lots: 1,
      stop_loss: opportunity.stop_loss
    };
    this.showNewPositionForm = true;
  }
  
  getConfidenceColor(confidence: number): string {
    if (confidence >= 0.8) return '#10b981';
    if (confidence >= 0.6) return '#f59e0b';
    return '#ef4444';
  }
  
  getRiskLevelColor(riskLevel: string): string {
    switch (riskLevel) {
      case 'LOW': return '#10b981';
      case 'MODERATE': return '#f59e0b';
      case 'HIGH': return '#ef4444';
      default: return '#64748b';
    }
  }
  
  isInProfit(): boolean {
    if (!this.selectedPosition) return false;
    return this.selectedPosition.unrealized_pnl >= 0;
  }
  
  getRecommendationColor(action: string): string {
    switch (action) {
      case 'ADD_POSITION': return '#10b981';
      case 'MOVE_STOP': return '#3b82f6';
      case 'PARTIAL_EXIT': return '#f59e0b';
      case 'CLOSE_ALL': return '#ef4444';
      default: return '#64748b';
    }
  }
  
  getActionGuidance(): string {
    if (!this.selectedPosition || !this.pyramidPlan) return '';
    
    const rec = this.pyramidPlan.current_recommendation;
    const pnl = this.selectedPosition.unrealized_pnl;
    
    if (pnl < 0) {
      return '⚠️ Position is in loss. Wait for profit before adding more lots.';
    }
    
    if (rec.action === 'ADD_POSITION') {
      return '✅ Price reached target. Good time to add position.';
    }
    
    if (rec.action === 'MOVE_STOP') {
      return '📈 Trail your stop loss to protect profits.';
    }
    
    if (rec.action === 'PARTIAL_EXIT') {
      return '💰 Consider taking partial profits at this level.';
    }
    
    if (rec.action === 'CLOSE_ALL') {
      return '🚪 Consider closing the position now.';
    }
    
    return '⏳ Hold current position. Wait for price to reach next target.';
  }
}
