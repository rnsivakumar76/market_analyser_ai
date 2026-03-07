"""
Domain constants — every magic number lives here.

Grouping convention:
  INDICATOR_*   — technical indicator parameters
  SIGNAL_*      — scoring weights and thresholds
  FILTER_*      — hard-filter thresholds
  VOLATILITY_*  — ATR / HV regime boundaries
  FIB_*         — Fibonacci ratios
  POSITION_*    — position-sizing parameters
  RVOL_*        — relative volume thresholds
  PULLBACK_*    — pullback detection parameters
  MACD_*        — MACD calculation spans
  BB_*          — Bollinger Bands parameters
  WARNING_*     — pullback warning scoring
"""

# ── Technical Indicators ────────────────────────────────────────────────────
INDICATOR_RSI_PERIOD: int = 14
INDICATOR_RSI_OVERSOLD: float = 30.0
INDICATOR_RSI_OVERBOUGHT: float = 70.0
INDICATOR_RSI_BULLISH_THRESHOLD: float = 55.0
INDICATOR_RSI_BEARISH_THRESHOLD: float = 45.0

INDICATOR_ATR_PERIOD: int = 14
INDICATOR_ADX_PERIOD: int = 14
INDICATOR_ADX_STRONG_TREND: float = 30.0
INDICATOR_ADX_DEVELOPING_TREND: float = 20.0

INDICATOR_FAST_MA_PERIOD: int = 20
INDICATOR_SLOW_MA_PERIOD: int = 50
INDICATOR_VWAP_PERIOD: int = 20
INDICATOR_VWAP_OVEREXTENDED_PCT: float = 1.5

INDICATOR_LRL_PERIOD: int = 20          # Linear regression lookback for line of least resistance
INDICATOR_LRL_SLOPE_THRESHOLD: float = 0.001  # Normalised slope (0.1% per bar)

# ── MACD ────────────────────────────────────────────────────────────────────
MACD_FAST_SPAN: int = 12
MACD_SLOW_SPAN: int = 26
MACD_SIGNAL_SPAN: int = 9

# ── Bollinger Bands ─────────────────────────────────────────────────────────
BB_PERIOD: int = 20
BB_STD_DEV: int = 2

# ── Fibonacci Ratios ────────────────────────────────────────────────────────
FIB_RET_236: float = 0.236
FIB_RET_382: float = 0.382
FIB_RET_500: float = 0.500
FIB_RET_618: float = 0.618
FIB_EXT_1272: float = 1.272
FIB_EXT_1618: float = 1.618
FIB_LOOKBACK_BARS: int = 60            # How far back to find swing high/low

# ── Signal Scoring Weights ──────────────────────────────────────────────────
SIGNAL_WEIGHT_TREND: int = 40          # Monthly trend contribution (max ±40)
SIGNAL_WEIGHT_PULLBACK: int = 30       # Weekly pullback contribution (max ±30)
SIGNAL_WEIGHT_STRENGTH: int = 30       # Daily strength contribution (max ±30)

SIGNAL_PULLBACK_FULL_SCORE: int = 30   # Near support in uptrend
SIGNAL_PULLBACK_HALF_SCORE: int = 15   # Pullback detected, not yet at support
SIGNAL_PULLBACK_NO_PULLBACK: int = 5   # Extended from support

SIGNAL_STRENGTH_ALIGNED: int = 30      # Daily signal matches trend
SIGNAL_STRENGTH_COUNTER: int = 10      # Daily signal fights trend
SIGNAL_BEARISH_CONT: int = 20          # Downtrend continuation
SIGNAL_BEARISH_BOUNCE: int = 10        # Bounce in downtrend

# ── Signal Thresholds ───────────────────────────────────────────────────────
SIGNAL_CONVICTION_THRESHOLD: int = 70  # Minimum score for trade-worthy
SIGNAL_DEVELOPING_THRESHOLD: int = 20  # Below this = truly neutral

# ── ADX Regime Boundaries (for adaptive scoring) ─────────────────────────────
SIGNAL_ADX_RANGING: float = 20.0   # ADX < 20  → no clear trend (mean-reversion valid)
SIGNAL_ADX_TRENDING: float = 30.0  # ADX >= 30 → trending (momentum valid)
SIGNAL_ADX_STRONG: float = 45.0    # ADX >= 45 → strong trend

# ── Regime-Adaptive Weight Table ──────────────────────────────────────────────
# Total always = 100 so the SIGNAL_CONVICTION_THRESHOLD (70) needs no change.
# In RANGING markets pullback-to-support is more reliable than raw trend direction.
# In TRENDING markets, the prevailing trend dominates and mean-reversion weight drops.
SIGNAL_ADX_REGIME_WEIGHTS: dict = {
    "RANGING":  {"trend": 25, "pullback": 45, "strength": 30},  # ADX < 20
    "NORMAL":   {"trend": 40, "pullback": 30, "strength": 30},  # 20 <= ADX < 30
    "TRENDING": {"trend": 50, "pullback": 20, "strength": 30},  # 30 <= ADX < 45
    "STRONG":   {"trend": 55, "pullback": 15, "strength": 30},  # ADX >= 45
}

# ── Hard Filters ────────────────────────────────────────────────────────────
FILTER_ADX_THRESHOLD: float = 25.0     # ADX must exceed this for trade-worthy
FILTER_MACRO_SCORE_PENALTY: int = 20   # Score reduction when macro shield active

# ── Volatility Regimes ──────────────────────────────────────────────────────
VOLATILITY_LOW_PERCENTILE: float = 25.0
VOLATILITY_NORMAL_PERCENTILE: float = 60.0
VOLATILITY_ELEVATED_PERCENTILE: float = 80.0

VOLATILITY_ATR_COMPRESSION_RATIO: float = 0.8   # ATR < 80% of avg = compressed
VOLATILITY_HV_ANNUALISE_FACTOR: float = 252.0

# ── ATR Multipliers (Stop Loss / Take Profit) ───────────────────────────────
VOLATILITY_ATR_SL_MULTIPLIER: float = 1.5
VOLATILITY_ATR_TP1_MULTIPLIER: float = 1.0
VOLATILITY_ATR_TP2_MULTIPLIER: float = 2.0
VOLATILITY_ATR_TP3_MULTIPLIER: float = 3.0

# ── Regime-Adaptive ATR Multiplier Table ─────────────────────────────────────
# Multipliers are widened in ELEVATED/EXTREME regimes (fast markets need room)
# and tightened in COMPRESSED/LOW regimes (range contraction → precision entries).
# Keys match the regime strings returned by _calc_volatility_regime().
# R/R maintained at 2:1 across all regimes (tp3 / sl = 2.0).
VOLATILITY_REGIME_ATR_MULTIPLIERS: dict = {
    "LOW":      {"sl": 1.0, "tp1": 0.75, "tp2": 1.5, "tp3": 2.0},
    "NORMAL":   {"sl": 1.5, "tp1": 1.0,  "tp2": 2.0, "tp3": 3.0},
    "ELEVATED": {"sl": 2.0, "tp1": 1.25, "tp2": 2.5, "tp3": 4.0},
    "EXTREME":  {"sl": 2.5, "tp1": 1.5,  "tp2": 3.0, "tp3": 5.0},
}

# ── Breakout Detection ──────────────────────────────────────────────────────
BREAKOUT_DONCHIAN_PERIOD: int = 20      # Donchian channel lookback
BREAKOUT_MIN_BARS_REQUIRED: int = 21

# ── Pullback Detection ──────────────────────────────────────────────────────
PULLBACK_THRESHOLD_PCT: float = 0.03   # 3% from recent high = pullback
PULLBACK_SUPPORT_TOLERANCE_PCT: float = 0.02  # Within 2% of support = near support

# ── Pullback Warning Scoring ─────────────────────────────────────────────────
WARNING_RSI_DIVERGENCE_WEIGHT: int = 2
WARNING_MACD_WEAKENING_WEIGHT: int = 1
WARNING_ATR_COMPRESSION_WEIGHT: int = 1
WARNING_BB_REENTRY_WEIGHT: int = 1
WARNING_STRUCTURE_BREAK_WEIGHT: int = 3
WARNING_TRIGGER_SCORE: int = 3         # Score >= this = warning active
WARNING_LOOKBACK_BARS: int = 20

# ── Position Sizing ─────────────────────────────────────────────────────────
POSITION_CORRELATION_FLOOR: float = 0.3     # Below this = no penalty
POSITION_CORRELATION_MAX_PENALTY: float = 0.6  # Max 60% size reduction
POSITION_CORRELATION_PENALTY_SLOPE: float = 1.0
POSITION_FALLBACK_SL_MULTIPLIER: float = 1.5  # When SL ≈ entry, use ATR * this

# ── Relative Volume (RVOL) ───────────────────────────────────────────────────
RVOL_LOOKBACK_DAYS: int = 5
RVOL_HIGH_INTENT: float = 1.8
RVOL_MODERATE: float = 1.5
RVOL_HIGH: float = 2.0

# ── Commodity-Specific Thresholds ──────────────────────────────────────────
COMMODITY_DXY_RISE_THRESHOLD: float = 0.2
COMMODITY_YIELD_RISE_THRESHOLD: float = 0.1
COMMODITY_DXY_FALL_THRESHOLD: float = -0.2
COMMODITY_YIELD_FALL_THRESHOLD: float = -0.1
COMMODITY_BTC_DXY_SPIKE: float = 0.3

# ── Signal Conflict Detection ───────────────────────────────────────────────
CONFLICT_STRONG_ADX: float = 35.0      # ADX >= this triggers ADX/direction mismatch check

# ── Std-Dev Bands ────────────────────────────────────────────────────────────
STDBAND_PERIOD: int = 20
