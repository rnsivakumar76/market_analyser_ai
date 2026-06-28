---
trigger: always_on
---

# Architecture Guardrails (non-negotiable)

These are project invariants. Follow them on EVERY change. When a fix tempts you
to violate one, stop and flag it instead of silently working around it.

## Layering (strict)
- `domain/` = pure calculations only (no pandas, no I/O, no framework). All
  thresholds/weights/magic numbers live in `domain/constants.py`.
- `app/analyzers/` = thin adapters that delegate math to `domain/`. Do NOT
  re-implement indicator/level/scoring math here — call the domain function.
- `app/models.py` = the data contract (Pydantic). It is the single source of
  truth for response shape.
- `app/main.py` = orchestration only. No business math inline.

## Single source of truth (SSOT)
- A given concept is computed in ONE place and consumed everywhere else.
- Trade levels (entry/stop/targets) come ONLY from the canonical `TradePlan`
  (`app/analyzers/trade_plan_builder.py`). The level card, Strategic Action,
  Battle Plan and scaling text MUST render from it — never recompute levels.
- If you need a value that already exists, import/pass it; do not duplicate it.

## Change discipline
- Make the MINIMAL upstream fix at the root cause. No downstream patches that
  mask a bug computed elsewhere.
- Do not edit unrelated files/sections to "improve" them in a bugfix. Stay in
  scope; propose other changes separately.
- Never weaken/delete tests to make something pass.
- Preserve existing public function signatures; add optional params instead of
  breaking callers.

## Before coding
- For anything touching levels, signals, or indicators, confirm WHICH layer owns
  it and edit there. Read `ARCHITECTURE.md` only when you need the deep map.

## Environment
- Shell is PowerShell: never chain with `&&` (use `;`). Never run `cd` in a
  command — set the working directory instead.
- Deploys go through the git pipeline (push to `develop`); do not hand-deploy.
