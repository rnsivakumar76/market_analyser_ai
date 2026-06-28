---
description: Add a new analyzer/feature following the layered architecture
---

1. Decide the layer: pure math → `domain/<area>/`; orchestration/adapter → `app/analyzers/`.
2. Put all constants/thresholds in `domain/constants.py` (never hardcode in analyzers).
3. Implement pure logic in `domain/` with a dataclass return; add a unit test alongside it.
4. Add a thin adapter in `app/analyzers/` that delegates to the domain function and maps to a Pydantic model.
5. Add/extend the Pydantic model in `app/models.py` (optional fields for backward-compat with cached payloads).
6. Export the adapter in `app/analyzers/__init__.py` (`import` + `__all__`).
7. Wire it into `app/main.py` orchestration only — no business math inline.
8. If it produces trade levels, derive them from the canonical `TradePlan`; do not recompute.
// turbo
9. Validate syntax: `.\backend\venv\Scripts\python.exe -c "import ast; ast.parse(open(r'<file>', encoding='utf-8').read()); print('OK')"`
