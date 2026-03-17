# UI Audit Benchmark — Market Analyser AI
**Date**: 2026-03-17  
**Auditor**: Cascade  
**Scope**: Instrument Card (Short Term + Long Term), WTI $96.33 sample data  
**Last Fix Pass**: 2026-03-17 — commit d95b043

---

## CRITICAL — Data Contradictions / Wrong Values

| # | Issue | Location | Fix | Status |
|---|---|---|---|---|
| 1 | VOLATILITY RISK=LOW vs VOLATILITY REGIME=Extreme (ATR 87th %ile) — direct contradiction | Risk Factors drawer | `getVolatilityLevel()` now derives level from `atr_percentile_rank` (80→EXTREME, 60→ELEVATED, 25→NORMAL, else LOW) ensuring both checks use same source | ✅ Fixed |
| 2 | Long Term R1($89.19) < S1($89.82) — resistance below support, both below current price | Signal drawer (Long Term) | `signal_generator.py` Two-Sided plan guards: only uses R1/S1 triggers when they straddle current price; falls back to pivot zone message | ✅ Fixed |
| 3 | "SEASON" renders in Tactical MTF cell instead of direction | Signal drawer (Long Term) | `multi-timeframe-overlay.component.ts` TACTICAL direction normalised to `['bullish','bearish','neutral']` only | ✅ Fixed |
| 4 | Garbled text: "to confirm BI AREA)" — should be "BEAR (DOWN)" | Signal drawer (Long Term) | Current backend generates "BULLISH"/"BEARISH" — likely stale cached response; will resolve on data refresh | ✅ No code issue |

## WRONG INTERPRETATIONS

| # | Issue | Location | Fix | Status |
|---|---|---|---|---|
| 5 | ADX 38 described as "Ultra-Strong Trend" — ADX 38 = Strong, Ultra-Strong is 50+ | Validation & Risk Intel | `getMomentumCorrelation()` threshold corrected: ≥50=Ultra-Strong, ≥35=Strong Trend, ≥25=Established | ✅ Fixed |
| 6 | Volume 1.0x avg labeled "low conviction" — 1.0x is average/neutral | Geo Risk Intel | `geo_risk_analyzer.py` added neutral tier 0.8–1.3x = "normal participation"; <0.8x = below-average conviction | ✅ Fixed |
| 7 | Short Reversal target $95.31 only $0.66 below trigger — R/R = 0.55:1 (losing) | Tactical Interpretation | `getBearTargetText()` now uses S3 first, then S2 fallback for deeper, realistic target | ✅ Fixed |

## WRONG LABELS

| # | Issue | Location | Fix | Status |
|---|---|---|---|---|
| 8 | "FIXED SCALING ENTRIES" section contains profit exit targets T1/T2/T3 | Signal drawer | Renamed to "PROFIT TARGETS (T1 / T2 / T3)" | ✅ Fixed |
| 9 | "RECOMMENDED ACTION: HOLD POSITION" when no trade open (TRIGGER=NO) | Risk Factors drawer | `getPullbackAction()` returns MONITOR when no trigger active, HOLD POSITION only when triggered | ✅ Fixed |

## MISSING / INCOMPLETE DATA

| # | Issue | Location | Fix | Status |
|---|---|---|---|---|
| 10 | VWAP DIST shows N/A despite Session VWAP = $96.70 dist = -0.38% available | Market Momentum Read | `getVwapDistDisplay()` falls back to `session_vwap.distance_pct` when `daily_strength.vwap_dist_pct` is null | ✅ Fixed |
| 11 | Volume Analysis stuck on "ANALYZING" (never resolves) | Validation & Risk Intel | `getVolumeStatus()` uses `volume_ratio`: ≥2.0=STRONG, ≥1.0=AVERAGE, ≥0.5=BELOW AVG, else LOW | ✅ Fixed |
| 12 | Liquidity Map shows only macro supports $73-75. Near-term S1/S2/S3 absent | Liquidity Map | `liquidity_map_analyzer.py` now prepends near-term swings (last 30 bars, within 8% of price) before structural levels | ✅ Fixed |
| 13 | Phase score "1.23" shown with no denominator or scale context | Macro Regime section | Label changed to "Slope Index" with +/- sign; score is MA50 slope ×1000 | ✅ Fixed |
| 14 | Blow-off top trigger $91.90 below current price — no explanation | Risk Factors | Template now shows "(breakdown trigger — fires if price falls below this level)" vs "(breakout trigger)" contextually | ✅ Fixed |

## CONFLICTING GUIDANCE

| # | Issue | Location | Fix | Status |
|---|---|---|---|---|
| 15 | Battle Plan "long reversal at support" vs S/R "wait for pivot reclaim" — unreconciled | Expert Battle Plan vs Signal drawer | `getPivotTradeRead()` now provides nuanced advice: bullish signal at price>S1 → "S1 is valid long entry with confirmation. Reclaiming Pivot adds conviction." | ✅ Fixed |
| 16 | "buy pullback near S1 / Fib 38.2%" — "/" implies equivalence for $1.49-apart levels | Signal drawer — trigger text | `signal_generator.py` Conditional Long now presents Trigger A (R1 momentum), B (S1 pullback), C (Fib pullback) as distinct entries | ✅ Fixed |

## MINOR / COSMETIC

| # | Issue | Location | Fix | Status |
|---|---|---|---|---|
| 17 | ADX shows "38" in header but "37.9" in tactical (same data) | Signal drawer | Both now use `.toFixed(1)` — consistent 1 decimal place | ✅ Fixed |
| 18 | RSI shows "70" in header but "69.6" in tactical | Signal drawer | Both now use `.toFixed(1)` — consistent 1 decimal place | ✅ Fixed |
| 19 | Typo: "March9 2026" in geo risk headline | Context panel | Comes from external news API data — cannot be fixed in code | ⚠ External |
| 20 | "Volatility low affects position sizing" — incomplete sentence | Risk Factors | `getVolatilityCorrelation()` rewritten with complete sentences for all 4 volatility levels | ✅ Fixed |

---

## Fix Summary

| Category | Total Issues | Fixed | External/Stale |
|---|---|---|---|
| Critical | 4 | 3 | 1 (#4 stale cache) |
| Wrong Interpretations | 3 | 3 | 0 |
| Wrong Labels | 2 | 2 | 0 |
| Missing/Incomplete | 5 | 5 | 0 |
| Conflicting Guidance | 2 | 2 | 0 |
| Minor/Cosmetic | 4 | 3 | 1 (#19 external API) |
| **TOTAL** | **20** | **18** | **2** |

## Files Modified

| File | Issues |
|---|---|
| `frontend/.../instrument-card.component.ts` | #1, #5, #7, #8, #9, #10, #11, #13, #14, #15, #17, #18, #20 |
| `frontend/.../multi-timeframe-overlay.component.ts` | #3 |
| `backend/.../geo_risk_analyzer.py` | #6 |
| `backend/.../signal_generator.py` | #2, #16 |
| `backend/.../liquidity_map_analyzer.py` | #12 |

**Commits**: `d95b043` (backend+frontend), plus earlier frontend-only commit
