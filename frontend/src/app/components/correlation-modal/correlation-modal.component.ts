import { Component, output, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CorrelationData } from '../../services/market-analyzer.service';
import { CorrelationHeatmapComponent } from '../correlation-heatmap/correlation-heatmap.component';

@Component({
    selector: 'app-correlation-modal',
    standalone: true,
    imports: [CommonModule, CorrelationHeatmapComponent],
    template: `
    <div class="modal-overlay" (click)="close.emit()">
      <div class="modal-content" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h2>Market Correlation Analysis</h2>
          <button class="close-btn" (click)="close.emit()">&times;</button>
        </div>
        
        <div class="modal-body">
          <app-correlation-heatmap [data]="data()"></app-correlation-heatmap>
          
          <div class="info-section">
            <h4>How to Read Correlated Risk</h4>
            <ul>
              <li><strong>Positive (>0.7)</strong>: These assets move in lockstep. If you have bullish signals on both, you are doubling down on the same market move. Consider reducing size.</li>
              <li><strong>Neutral (-0.2 to 0.2)</strong>: These are independent assets. Excellent for diversification.</li>
              <li><strong>Negative (<-0.5)</strong>: These move in opposite directions. Useful for hedging your portfolio.</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  `,
    styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(17, 17, 27, 0.85);
      backdrop-filter: blur(8px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2000;
    }

    .modal-content {
      background: #1e1e2e;
      width: 95%;
      max-width: 900px;
      border-radius: 16px;
      border: 1px solid #313244;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
      overflow: hidden;
    }

    .modal-header {
      padding: 20px 24px;
      border-bottom: 1px solid #313244;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .modal-header h2 {
      margin: 0;
      font-size: 1.25rem;
      color: #cdd6f4;
    }

    .close-btn {
      background: none;
      border: none;
      color: #6c7086;
      font-size: 2rem;
      cursor: pointer;
      line-height: 1;
    }

    .modal-body {
      padding: 24px;
      max-height: 80vh;
      overflow-y: auto;
    }

    .info-section {
      margin-top: 24px;
      padding: 16px;
      background: rgba(137, 180, 250, 0.1);
      border-radius: 8px;
    }

    .info-section h4 {
      margin: 0 0 12px 0;
      color: #89b4fa;
      font-size: 0.9rem;
      text-transform: uppercase;
    }

    .info-section ul {
      margin: 0;
      padding-left: 20px;
      color: #a6adc8;
      font-size: 0.85rem;
    }

    .info-section li {
      margin-bottom: 8px;
    }
  `]
})
export class CorrelationModalComponent {
    data = input<CorrelationData | null>(null);
    close = output();
}
