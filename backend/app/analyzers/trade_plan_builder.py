"""
Trade Plan Builder — single source of truth for trade levels.
============================================================

Historically, entry/stop/target numbers were computed independently in three
places (the volatility analyzer for the level card, the signal generator for the
Strategic Action narrative, and the day-trading expert for the Battle Plan).
Those derivations could diverge — e.g. an entry of $99 displayed while price was
$71. This module reconciles everything into ONE canonical ``TradePlan`` that all
surfaces render from.

The numeric ladder (entry / stop / TP1-3) is taken from the already-reconciled
``VolatilityAnalysis`` (which is ATR + sanity-bounded structure aware). Pivots
and the opening range are layered in ONLY as structural context (invalidation
level and human-readable basis labels), never as a competing set of trade levels.
"""

from typing import Optional, Dict, Any
import logging

from ..models import TradePlan, VolatilityAnalysis, TechnicalAnalysis

logger = logging.getLogger(__name__)


def _direction_label(signal_direction: str) -> str:
    """Map a Signal value ('bullish'/'bearish'/'neutral') to long/short/neutral."""
    if signal_direction == "bullish":
        return "long"
    if signal_direction == "bearish":
        return "short"
    return "neutral"


def build_trade_plan(
    signal_direction: str,
    current_price: float,
    volatility: VolatilityAnalysis,
    tech_indicators: Optional[TechnicalAnalysis] = None,
    is_actionable: bool = False,
    or_data: Optional[Dict[str, Any]] = None,
) -> Optional[TradePlan]:
    """Produce the canonical TradePlan from the final reconciled levels.

    Args:
        signal_direction: Final trade recommendation ('bullish'/'bearish'/'neutral').
        current_price:    Live price (used for entry-basis labelling).
        volatility:       The FINAL VolatilityAnalysis (post-recalc) — the numeric
                          source of truth for entry/stop/targets.
        tech_indicators:  Pivots/fib for structural invalidation context.
        is_actionable:    Whether the setup is tradeable now (trade_worthy).
        or_data:          Opening-range dict ({'or_high','or_low','broken'}) when available.

    Returns:
        TradePlan, or None when there is no usable volatility data.
    """
    if volatility is None or not volatility.atr or volatility.atr <= 0:
        return None
    if not current_price or current_price <= 0:
        return None

    direction = _direction_label(signal_direction)

    entry = float(volatility.entry_price if volatility.entry_price else current_price)
    sl = float(volatility.stop_loss)
    tp1 = float(volatility.take_profit_level1 if volatility.take_profit_level1 is not None else volatility.take_profit)
    tp2 = float(volatility.take_profit_level2 if volatility.take_profit_level2 is not None else volatility.take_profit)
    tp3 = float(volatility.take_profit)
    rr = float(volatility.risk_reward_ratio)

    # ── Entry basis label ────────────────────────────────────────────────────
    entry_dev = abs(entry - current_price) / current_price if current_price else 0.0
    if entry_dev < 0.001:
        entry_basis = f"Market entry near current price (${entry:.2f})"
    elif direction == "short":
        entry_basis = f"Pending short — sell a bounce up to ${entry:.2f}"
    elif direction == "long":
        entry_basis = f"Pending long — buy a pullback down to ${entry:.2f}"
    else:
        entry_basis = f"Reference entry ${entry:.2f}"

    # ── Structural invalidation (pivots / opening range) ─────────────────────
    invalidation: Optional[float] = None
    or_high = float((or_data or {}).get("or_high") or 0.0)
    or_low = float((or_data or {}).get("or_low") or 0.0)
    pp = tech_indicators.pivot_points if (tech_indicators and tech_indicators.pivot_points) else None

    if direction == "long":
        structural = or_low if or_low > 0 else (pp.s1 if pp else 0.0)
        if structural > 0:
            invalidation = round(structural, 2)
            stop_basis = (f"Hard stop ${sl:.2f} (ATR-buffered); plan INVALID on a close "
                          f"below ${invalidation:.2f}.")
        else:
            stop_basis = f"Hard stop ${sl:.2f} (ATR-buffered)."
    elif direction == "short":
        structural = or_high if or_high > 0 else (pp.r1 if pp else 0.0)
        if structural > 0:
            invalidation = round(structural, 2)
            stop_basis = (f"Hard stop ${sl:.2f} (ATR-buffered); plan INVALID on a close "
                          f"above ${invalidation:.2f}.")
        else:
            stop_basis = f"Hard stop ${sl:.2f} (ATR-buffered)."
    else:
        stop_basis = f"Reference band edge ${sl:.2f} (no directional stop)."

    # ── Targets ladder ────────────────────────────────────────────────────────
    if direction == "neutral":
        target_basis = f"Expected range ${min(sl, tp3):.2f} – ${max(sl, tp3):.2f} (no directional targets)."
        narrative = (f"NEUTRAL — no directional edge. {target_basis} "
                     f"Use conditional triggers rather than forcing an entry.")
    else:
        target_basis = (f"Scale out: TP1 ${tp1:.2f} (de-risk, move stop to break-even) → "
                        f"TP2 ${tp2:.2f} → TP3 ${tp3:.2f} (runner).")
        readiness = "Actionable now" if is_actionable else "Conditional — await trigger confirmation"
        narrative = (f"{direction.upper()} plan ({readiness}). {entry_basis}. "
                     f"{stop_basis} {target_basis} R:R {rr:.2f}.")

    plan = TradePlan(
        direction=direction,
        entry=round(entry, 4),
        stop_loss=round(sl, 4),
        take_profit_1=round(tp1, 4),
        take_profit_2=round(tp2, 4),
        take_profit_3=round(tp3, 4),
        risk_reward=round(rr, 2),
        is_actionable=bool(is_actionable),
        entry_basis=entry_basis,
        stop_basis=stop_basis,
        target_basis=target_basis,
        invalidation=invalidation,
        narrative=narrative,
    )
    logger.info(
        f"[TRADE_PLAN] dir={direction} entry={plan.entry} sl={plan.stop_loss} "
        f"tp1={plan.take_profit_1} tp3={plan.take_profit_3} rr={plan.risk_reward} "
        f"actionable={plan.is_actionable}"
    )
    return plan
