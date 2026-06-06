"""
Trade Verdict — single, decisive instruction layer.

The composite score, MTF conflict, breakout guard and filters all produce
fragments of truth. This module collapses them into ONE unambiguous headline so
the user is never left reconciling 6 panels under pressure:

  TRADE_LONG   (green)  — execute a long now
  TRADE_SHORT  (red)    — execute a short now
  WAIT         (amber)  — bias exists but unconfirmed / conflicted; do not enter yet
  STAND_ASIDE  (slate)  — no edge; keep capital protected

Core principle: the macro trend sets the bias, but the tradeable timeframe must
confirm before a TRADE verdict. When they disagree, the verdict is WAIT — never
a directional buy/sell.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"

TRADE_LONG = "TRADE_LONG"
TRADE_SHORT = "TRADE_SHORT"
WAIT = "WAIT"
STAND_ASIDE = "STAND_ASIDE"


@dataclass(frozen=True)
class VerdictResult:
    verdict: str        # TRADE_LONG | TRADE_SHORT | WAIT | STAND_ASIDE
    headline: str       # short, bold instruction
    detail: str         # one-line supporting explanation
    color: str          # green | red | amber | slate


def compute_verdict(
    recommendation: str,
    trade_worthy: bool,
    score: int,
    conflict_type: str = "none",
    conflict_severity: str = "none",
    conflict_guidance: str = "",
    breakout_trap: bool = False,
    breakout_reason: str = "",
) -> VerdictResult:
    """
    Resolve all signal fragments into a single verdict.

    Priority order (highest first):
      1. Breakout trap → WAIT (do not chase the trap), unless a real trade is confirmed.
      2. MTF / ADX conflict while not trade-worthy → WAIT with the conflict guidance.
      3. Trade-worthy + directional → TRADE_LONG / TRADE_SHORT.
      4. Directional bias but not trade-worthy → WAIT (conditional, await trigger).
      5. Otherwise → STAND_ASIDE.
    """
    # 3. A fully confirmed trade overrides softer cautions.
    if trade_worthy and recommendation == BULLISH:
        return VerdictResult(
            verdict=TRADE_LONG,
            headline="TRADE LONG — setup confirmed",
            detail="Trend, momentum and trigger align. Execute the long plan with disciplined risk.",
            color="green",
        )
    if trade_worthy and recommendation == BEARISH:
        return VerdictResult(
            verdict=TRADE_SHORT,
            headline="TRADE SHORT — setup confirmed",
            detail="Trend, momentum and trigger align. Execute the short plan with disciplined risk.",
            color="red",
        )

    # 1. Trap risk: explicit "do not chase" guidance.
    if breakout_trap:
        return VerdictResult(
            verdict=WAIT,
            headline="WAIT — breakout trap risk",
            detail=breakout_reason or "Counter-trend breakout detected. Do not chase; wait for trend alignment.",
            color="amber",
        )

    # 2. Multi-timeframe / ADX conflict.
    if conflict_type and conflict_type != "none" and conflict_severity in ("high", "medium"):
        return VerdictResult(
            verdict=WAIT,
            headline="WAIT — timeframes disagree",
            detail=conflict_guidance or "Long-term trend and short-term momentum conflict. Wait for confirmation.",
            color="amber",
        )

    # 4. Directional bias but unconfirmed.
    if recommendation == BULLISH:
        return VerdictResult(
            verdict=WAIT,
            headline="WAIT — bullish bias, not yet confirmed",
            detail="Bias is up but the trigger hasn't fired. Enter only on confirmation; don't chase mid-range.",
            color="amber",
        )
    if recommendation == BEARISH:
        return VerdictResult(
            verdict=WAIT,
            headline="WAIT — bearish bias, not yet confirmed",
            detail="Bias is down but the trigger hasn't fired. Enter only on breakdown/rejection confirmation.",
            color="amber",
        )

    # 5. No edge.
    return VerdictResult(
        verdict=STAND_ASIDE,
        headline="STAND ASIDE — no edge",
        detail="No directional or trigger alignment. Keep capital protected until structure confirms.",
        color="slate",
    )
