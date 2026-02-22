# Market Analyzer

A multi-timeframe market analysis tool that helps identify trading opportunities by analyzing:
- **Monthly Trend**: Using 20/50 day moving averages to determine overall trend direction
- **Weekly Pullback**: Detecting pullbacks to support levels within the trend
- **Daily Strength**: RSI, volume, and price action for entry timing

## Architecture

```
market-analyzer/
├── backend/           # Python FastAPI backend
│   ├── app/
│   │   ├── analyzers/ # Analysis modules
│   │   ├── main.py    # API endpoints
│   │   └── ...
│   ├── config/
│   │   └── instruments.yaml  # Instrument configuration
│   └── requirements.txt
└── frontend/          # Angular dashboard
    └── src/
```

## Quick Start (Docker)

```bash
cd market-analyzer
docker-compose up --build
```

Open **http://localhost:4200** in your browser.

To stop:
```bash
docker-compose down
```

## Manual Setup (Development)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# or: source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
ng serve
```

Open http://localhost:4200

## Configuration

Edit `backend/config/instruments.yaml` to customize:
- **instruments**: List of stock/ETF symbols to analyze
- **analysis parameters**: MA periods, RSI thresholds, pullback settings

## API Endpoints

- `GET /api/analyze` - Analyze all configured instruments
- `GET /api/analyze/{symbol}` - Analyze a single instrument
- `GET /api/instruments` - List configured instruments
- `GET /api/health` - Health check

## Trade Signal Logic

The tool generates a composite score (-100 to +100) based on:

| Condition | Score Impact |
|-----------|--------------|
| Bullish monthly trend | +40 |
| Pullback to support in uptrend | +30 |
| Daily strength confirms trend | +30 |

**Trade-worthy** signals have a score >= 50 (bullish) or <= -50 (bearish).

## Data Source

Uses [yfinance](https://github.com/ranaroussi/yfinance) for free US stock/ETF data.
