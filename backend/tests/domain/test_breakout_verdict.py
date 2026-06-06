"""
Unit tests for the breakout trap guard and the trade verdict layer.
Primitive types only — no Pydantic, no pandas.
"""

from domain.signals.breakout_guard import evaluate_breakout
from domain.signals.verdict import (
    compute_verdict,
    TRADE_LONG,
    TRADE_SHORT,
    WAIT,
    STAND_ASIDE,
)


# ── Breakout trap guard ───────────────────────────────────────────────────────

def test_no_breakout_returns_zero():
    r = evaluate_breakout("none", 0.9, "bullish", "bullish")
    assert r.score_delta == 0
    assert r.is_trap is False
    assert r.reason == ""


def test_counter_trend_bullish_breakout_is_trap():
    # Bull breakout while macro trend is DOWN = classic bull trap (the gold case).
    r = evaluate_breakout("bullish_breakout", 0.9, "bearish", "bearish")
    assert r.is_trap is True
    assert r.score_delta == 0
    assert "TRAP RISK" in r.reason


def test_counter_trend_bearish_breakout_is_trap():
    r = evaluate_breakout("bearish_breakout", 0.9, "bullish", "bullish")
    assert r.is_trap is True
    assert r.score_delta == 0


def test_thin_volume_breakout_gets_no_boost():
    # 1.1x avg volume => confidence 0.55 < 0.75 threshold.
    r = evaluate_breakout("bullish_breakout", 0.55, "bullish", "bullish")
    assert r.score_delta == 0
    assert r.is_trap is False
    assert "thin volume" in r.reason.lower()


def test_confirmed_aligned_bullish_breakout_full_boost():
    r = evaluate_breakout("bullish_breakout", 0.9, "bullish", "bullish", full_boost=15)
    assert r.score_delta == 15
    assert r.is_trap is False


def test_confirmed_aligned_bearish_breakout_full_boost():
    r = evaluate_breakout("bearish_breakout", 0.9, "bearish", "bearish", full_boost=15)
    assert r.score_delta == -15


def test_volume_ok_but_momentum_opposes_half_boost():
    # Trend neutral/aligned, volume ok, but daily momentum bearish on a bull breakout.
    r = evaluate_breakout("bullish_breakout", 0.9, "neutral", "bearish", full_boost=15)
    assert r.score_delta == 7  # half of 15, floored
    assert r.is_trap is False


# ── Trade verdict ─────────────────────────────────────────────────────────────

def test_confirmed_long_is_trade_long():
    v = compute_verdict("bullish", trade_worthy=True, score=80)
    assert v.verdict == TRADE_LONG
    assert v.color == "green"


def test_confirmed_short_is_trade_short():
    v = compute_verdict("bearish", trade_worthy=True, score=-80)
    assert v.verdict == TRADE_SHORT
    assert v.color == "red"


def test_breakout_trap_forces_wait():
    v = compute_verdict(
        "bullish", trade_worthy=False, score=60,
        breakout_trap=True, breakout_reason="Bull trap vs downtrend",
    )
    assert v.verdict == WAIT
    assert v.color == "amber"
    assert "trap" in v.headline.lower()


def test_mtf_conflict_forces_wait():
    # The gold scenario: bullish bias, not trade-worthy, MTF disagreement.
    v = compute_verdict(
        "bullish", trade_worthy=False, score=60,
        conflict_type="mtf_disagreement", conflict_severity="medium",
        conflict_guidance="Monthly up vs daily down — wait.",
    )
    assert v.verdict == WAIT
    assert "Monthly up" in v.detail


def test_trade_worthy_overrides_conflict():
    # A fully confirmed trade should not be downgraded to WAIT by a stale conflict flag.
    v = compute_verdict(
        "bullish", trade_worthy=True, score=85,
        conflict_type="mtf_disagreement", conflict_severity="medium",
    )
    assert v.verdict == TRADE_LONG


def test_conditional_bias_without_conflict_is_wait():
    v = compute_verdict("bullish", trade_worthy=False, score=40)
    assert v.verdict == WAIT


def test_neutral_no_edge_is_stand_aside():
    v = compute_verdict("neutral", trade_worthy=False, score=5)
    assert v.verdict == STAND_ASIDE
    assert v.color == "slate"
