"""
Domain layer — single source of truth for all computational logic.

Sub-packages:
  indicators  — pure technical indicator math (RSI, ATR, ADX, VWAP, MACD, Bollinger)
  levels      — price-level calculations (pivot points, fibonacci, std-dev bands, breakout)
  signals     — trade signal scoring, hard filters, conflict detection
  trading     — intraday constructs (RVOL, ORB, position sizing)

All public functions accept primitive Python/NumPy types (floats, arrays).
They never import pandas DataFrames or FastAPI models — that belongs in the adapter layer.
"""
