import { Component, Input, AfterViewInit, ViewChild, ElementRef, OnDestroy, HostListener, OnChanges, SimpleChanges } from '@angular/core';
import { createChart, IChartApi, ISeriesApi, ColorType } from 'lightweight-charts';
import { ChartData } from '../../services/market-analyzer.service';

@Component({
    selector: 'app-instrument-chart',
    template: `<div #chartContainer class="chart-container"></div>`,
    styles: [`
    .chart-container {
      width: 100%;
      height: 250px;
      border-radius: 8px;
      overflow: hidden;
      background: #1e1e2e;
      border: 1px solid rgba(137, 180, 250, 0.2);
    }
  `],
    standalone: true
})
export class InstrumentChartComponent implements AfterViewInit, OnDestroy, OnChanges {
    @ViewChild('chartContainer') chartContainer!: ElementRef;
    @Input() data: ChartData[] = [];
    @Input() symbol: string = '';

    private chart: IChartApi | null = null;
    private candleSeries: ISeriesApi<"Candlestick"> | null = null;
    private resizeObserver: ResizeObserver | null = null;

    ngAfterViewInit() {
        this.initChart();
        // If data arrived before chart was ready, set it now
        if (this.data && this.data.length > 0 && this.candleSeries) {
            this.candleSeries.setData(this.data);
            if (this.chart) {
                this.chart.timeScale().fitContent();
            }
        }
    }

    ngOnChanges(changes: SimpleChanges) {
        if (changes['data'] && this.candleSeries && this.data) {
            this.candleSeries.setData(this.data);
            if (this.chart) {
                this.chart.timeScale().fitContent();
            }
        }
    }

    private initChart() {
        if (!this.chartContainer) return;

        this.chart = createChart(this.chartContainer.nativeElement, {
            layout: {
                background: { type: ColorType.Solid, color: '#1e1e2e' },
                textColor: '#cdd6f4',
            },
            grid: {
                vertLines: { color: 'rgba(69, 71, 90, 0.3)' },
                horzLines: { color: 'rgba(69, 71, 90, 0.3)' },
            },
            rightPriceScale: {
                borderVisible: false,
            },
            timeScale: {
                borderVisible: false,
                timeVisible: true,
                secondsVisible: false,
            },
            width: this.chartContainer.nativeElement.clientWidth,
            height: 250,
            handleScroll: true,
            handleScale: true,
        });

        this.candleSeries = (this.chart as any).addCandlestickSeries({
            upColor: '#a6e3a1',
            downColor: '#f38ba8',
            borderVisible: false,
            wickUpColor: '#a6e3a1',
            wickDownColor: '#f38ba8',
        });

        if (this.data && this.data.length > 0 && this.candleSeries) {
            this.candleSeries.setData(this.data as any);
            this.chart.timeScale().fitContent();
        }

        this.resizeObserver = new ResizeObserver(entries => {
            if (entries.length === 0 || entries[0].target !== this.chartContainer.nativeElement) {
                return;
            }
            const newRect = entries[0].contentRect;
            if (this.chart && newRect.width > 0 && newRect.height > 0) {
                this.chart.applyOptions({ width: newRect.width, height: newRect.height });
            }
        });

        this.resizeObserver.observe(this.chartContainer.nativeElement);
    }

    ngOnDestroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        if (this.chart) {
            this.chart.remove();
        }
    }
}
