import { Component, OnInit } from '@angular/core';
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

@Component({
  selector: 'app-pyramid-manager',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pyramid-manager.component.html',
  styleUrls: ['./pyramid-manager.component.scss']
})
export class PyramidManagerComponent implements OnInit {
  positions: PyramidPosition[] = [];
  selectedPosition: PyramidPosition | null = null;
  pyramidPlan: PyramidPlan | null = null;
  
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
  
  isLoading = false;
  showNewPositionForm = false;
  
  constructor(private http: HttpClient) {}
  
  ngOnInit() {
    this.loadPositions();
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
    this.selectedPosition = position;
    this.loadPyramidPlan(position.id);
  }
  
  loadPyramidPlan(positionId: string) {
    this.isLoading = true;
    this.http.get<PyramidPlan>(`/api/pyramid/position/${positionId}/plan`).subscribe({
      next: (plan) => {
        this.pyramidPlan = plan;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading pyramid plan:', error);
        this.isLoading = false;
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
}
