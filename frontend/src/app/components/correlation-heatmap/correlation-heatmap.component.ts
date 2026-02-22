import { Component, input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CorrelationData } from '../../services/market-analyzer.service';

@Component({
    selector: 'app-correlation-heatmap',
    standalone: true,
    imports: [CommonModule],
    template: `
    @if (data() && data()!.labels.length > 0) {
      <div class="heatmap-container">
        <div class="heatmap-header">
          <h3>Market Correlation Heatmap</h3>
          <p>Identifies price similarities to detect sector-wide movements.</p>
        </div>
        
        <div class="matrix-wrapper">
          <table class="heatmap-table">
            <thead>
              <tr>
                <th></th>
                @for (label of data()!.labels; track label) {
                  <th class="col-label">{{ label }}</th>
                }
              </tr>
            </thead>
            <tbody>
              @for (row of data()!.matrix; track $index; let i = $index) {
                <tr>
                  <th class="row-label">{{ data()!.labels[i] }}</th>
                  @for (val of row; track $index; let j = $index) {
                    <td 
                      [style.background-color]="getHeatmapColor(val)"
                      [title]="data()!.labels[i] + ' vs ' + data()!.labels[j] + ': ' + val"
                    >
                      <span class="cell-val">{{ val }}</span>
                    </td>
                  }
                </tr>
              }
            </tbody>
          </table>
        </div>

        <div class="legend">
          <span class="legend-item"><span class="box high"></span> High Correlation (>0.7)</span>
          <span class="legend-item"><span class="box mid"></span> Moderate</span>
          <span class="legend-item"><span class="box low"></span> Inverse (<0)</span>
        </div>
      </div>
    }
  `,
    styles: [`
    .heatmap-container {
      background: #1e1e2e;
      border: 1px solid #313244;
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 32px;
    }

    .heatmap-header h3 {
      margin: 0;
      color: #cdd6f4;
      font-size: 1.25rem;
    }

    .heatmap-header p {
      color: #6c7086;
      font-size: 0.85rem;
      margin: 4px 0 20px 0;
    }

    .matrix-wrapper {
      overflow-x: auto;
      border-radius: 8px;
    }

    .heatmap-table {
      border-collapse: separate;
      border-spacing: 2px;
      width: 100%;
      min-width: 600px;
    }

    th, td {
      width: 50px;
      height: 50px;
      text-align: center;
      font-size: 0.75rem;
      border-radius: 3px;
      transition: transform 0.1s;
    }

    td:hover {
      transform: scale(1.1);
      z-index: 5;
      position: relative;
      cursor: crosshair;
    }

    .col-label {
      transform: rotate(-45deg);
      height: 60px;
      vertical-align: bottom;
      padding-bottom: 10px;
      color: #9399b2;
      font-weight: 600;
    }

    .row-label {
      text-align: right;
      padding-right: 12px;
      color: #9399b2;
      font-weight: 600;
    }

    .cell-val {
      color: rgba(255, 255, 255, 0.8);
      font-weight: 700;
      text-shadow: 0 1px 2px rgba(0,0,0,0.5);
    }

    .legend {
      display: flex;
      gap: 20px;
      margin-top: 20px;
      font-size: 0.75rem;
      color: #6c7086;
    }

    .legend-item { display: flex; align-items: center; gap: 6px; }
    .box { width: 12px; height: 12px; border-radius: 2px; }
    .box.high { background: #a6e3a1; }
    .box.mid { background: #89b4fa; }
    .box.low { background: #f38ba8; }
  `]
})
export class CorrelationHeatmapComponent {
    data = input<CorrelationData | null>(null);

    getHeatmapColor(val: number): string {
        // Pearson Correlation ranging -1 to 1
        if (val >= 0.8) return 'rgba(166, 227, 161, 0.9)';   // Strong Positive (Green)
        if (val >= 0.6) return 'rgba(166, 227, 161, 0.6)';   // Moderate Positive
        if (val >= 0.3) return 'rgba(137, 180, 250, 0.4)';   // Weak Positive (Blue-ish)
        if (val <= -0.5) return 'rgba(243, 139, 168, 0.8)';  // Strong Negative (Red)
        if (val <= -0.2) return 'rgba(243, 139, 168, 0.4)';  // Weak Negative
        return 'rgba(69, 71, 90, 0.3)';                      // Neutral (Gray)
    }
}
