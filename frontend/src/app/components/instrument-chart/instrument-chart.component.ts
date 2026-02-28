import { Component, Input, AfterViewInit, ViewChild, ElementRef, OnDestroy, OnChanges, SimpleChanges } from '@angular/core';
import { createChart, IChartApi, ISeriesApi, ColorType } from 'lightweight-charts';
import { ChartData } from '../../services/market-analyzer.service';

export interface ChartOverlayLevel {
    price: number;
    label: string;
    color: string;
    lineStyle?: number; // 0=solid, 1=dotted, 2=dashed, 3=large-dashed
}

@Component({
    selector: 'app-instrument-chart',
    template: `<div #chartContainer class="chart-container"></div>`,
    styles: [`
    .chart-container {
      width: 100%;
      height: 280px;
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
    @Input() overlayLevels: ChartOverlayLevel[] = [];

    private chart: IChartApi | null = null;
    private candleSeries: ISeriesApi<'Candlestick'> | null = null;
    private resizeObserver: ResizeObserver | null = null;
    private lineSeries: ISeriesApi<'Line'>[] = [];

    ngAfterViewInit() {
        this.initChart();
        if (this.data && this.data.length > 0 && this.candleSeries) {
            this.candleSeries.setData(this.data as any);
            this.chart?.timeScale().fitContent();
        }
        this.renderOverlays();
    }

    ngOnChanges(changes: SimpleChanges) {
        if (changes['data'] && this.candleSeries && this.data) {
            this.candleSeries.setData(this.data as any);
            this.chart?.timeScale().fitContent();
        }
        if ((changes['overlayLevels'] || changes['data']) && this.chart) {
            this.renderOverlays();
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
            rightPriceScale: { borderVisible: false },
            timeScale: {
                borderVisible: false,
                timeVisible: true,
                secondsVisible: false,
            },
            width: this.chartContainer.nativeElement.clientWidth,
            height: 280,
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
            if (entries.length === 0 || entries[0].target !== this.chartContainer.nativeElement) return;
            const newRect = entries[0].contentRect;
            if (this.chart && newRect.width > 0 && newRect.height > 0) {
                this.chart.applyOptions({ width: newRect.width, height: newRect.height });
            }
        });

        this.resizeObserver.observe(this.chartContainer.nativeElement);
    }

    private renderOverlays() {
        if (!this.chart || !this.data || this.data.length === 0) return;

        // Remove existing overlay lines
        for (const s of this.lineSeries) {
            try { this.chart.removeSeries(s); } catch (_) { }
        }
        this.lineSeries = [];

        if (!this.overlayLevels || this.overlayLevels.length === 0) return;

        // Use chart time range from candle data
        const times = this.data.map(d => d.time);
        const firstTime = times[0];
        const lastTime = times[times.length - 1];

        for (const level of this.overlayLevels) {
            try {
                const lineSeries: ISeriesApi<'Line'> = (this.chart as any).addLineSeries({
                    color: level.color,
                    lineWidth: 1,
                    lineStyle: level.lineStyle ?? 2, // dashed by default
                    priceLineVisible: false,
                    lastValueVisible: true,
                    title: level.label,
                    crosshairMarkerVisible: false,
                });
                lineSeries.setData([
                    { time: firstTime as any, value: level.price },
                    { time: lastTime as any, value: level.price },
                ]);
                this.lineSeries.push(lineSeries);
            } catch (_) { }
        }
    }

    ngOnDestroy() {
        if (this.resizeObserver) this.resizeObserver.disconnect();
        if (this.chart) this.chart.remove();
    }
}
