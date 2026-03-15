from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["ai-chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    sessionId: str
    intent: Literal["signal_explainer", "risk_coach", "setup_monitor", "general"] = "general"
    symbol: Optional[str] = None
    question: str
    strategyMode: Literal["long_term", "short_term"] = "long_term"
    analysisContext: Dict[str, Any] = Field(default_factory=dict)
    history: List[ChatMessage] = Field(default_factory=list)


class ChatUsage(BaseModel):
    inputTokens: int = 0
    outputTokens: int = 0
    estimatedCostUsd: float = 0.0


class ChatSafety(BaseModel):
    adviceType: Literal["educational"] = "educational"
    containsFinancialGuarantee: bool = False


class ChatResponse(BaseModel):
    answer: str
    modelUsed: str
    escalated: bool = False
    citations: List[str] = Field(default_factory=list)
    usage: ChatUsage = Field(default_factory=ChatUsage)
    safety: ChatSafety = Field(default_factory=ChatSafety)


def _select_model(question: str, intent: str) -> Tuple[str, bool]:
    deep_keywords = ("scenario", "portfolio", "macro", "intermarket", "multi-step", "deep")
    should_escalate = len(question) > 350 or any(k in question.lower() for k in deep_keywords)
    if intent in {"risk_coach", "general"}:
        should_escalate = should_escalate or len(question.split()) > 55

    default_model = os.environ.get("BEDROCK_MODEL_HAIKU", "anthropic.claude-3-haiku-20240307-v1:0")
    sonnet_model = os.environ.get("BEDROCK_MODEL_SONNET", "anthropic.claude-3-5-sonnet-20240620-v1:0")

    if should_escalate:
        return sonnet_model, True
    return default_model, False


def _build_context_citations(ctx: Dict[str, Any]) -> List[str]:
    citations: List[str] = []
    if "tradeSignal" in ctx:
        citations.append("analysisContext.tradeSignal")
    if "blowoffTop" in ctx:
        citations.append("analysisContext.blowoffTop")
    if "volatility" in ctx:
        citations.append("analysisContext.volatility")
    if "fundamentals" in ctx:
        citations.append("analysisContext.fundamentals")
    if "marketPhase" in ctx:
        citations.append("analysisContext.marketPhase")
    if "market_phase" in ctx:
        citations.append("analysisContext.market_phase")
    return citations


def _fallback_answer(question: str, ctx: Dict[str, Any], strategy_mode: str) -> str:
    trade_signal = ctx.get("tradeSignal") or {}
    blowoff = ctx.get("blowoffTop") or {}
    rec = trade_signal.get("recommendation", "neutral")
    score = trade_signal.get("score")
    reasons = trade_signal.get("reasons") or []
    reason_text = ", ".join(reasons[:3]) if reasons else "no strong tagged drivers yet"

    q = question.lower()
    lines: List[str] = []
    vol = ctx.get("volatility") or {}
    phase = (ctx.get("marketPhase") or ctx.get("market_phase") or {}).get("phase", "unknown")
    pullback = ctx.get("pullbackWarning") or {}
    pullback_level = pullback.get("pullback_level")
    execution_state = trade_signal.get("execution_state")
    size_hint = trade_signal.get("suggested_size_text")

    if "plan" in q or "monday" in q or "today" in q:
        lines.append(f"Plan stance: {rec.upper()} (score {score if score is not None else 'N/A'}) in {strategy_mode} mode.")
        lines.append(f"Setup phase: {phase}. Top drivers: {reason_text}.")
        if execution_state:
            lines.append(f"Execution state: {execution_state}.")
        if size_hint:
            lines.append(f"Sizing hint: {size_hint}.")
        if pullback_level:
            lines.append(f"Key area: monitor pullback zone around {pullback_level} for hold/rejection behavior.")
        if blowoff.get("applicable"):
            lines.append(
                f"Blow-off watch: phase={blowoff.get('phase', 'normal')}, "
                f"state={blowoff.get('entryState') or blowoff.get('entry_state', 'wait')}."
            )
        return "\n".join(lines)

    if "why" in q or "trade-worthy" in q or "trade worthy" in q or "setup" in q:
        lines.append(f"Bias: {rec.upper()} (score {score if score is not None else 'N/A'}).")
        lines.append(f"Why now: the score is being driven mainly by {reason_text}.")
        lines.append(f"Market phase is {phase}, so treat this as confirmation-first rather than prediction-first.")
        if pullback_level:
            lines.append(f"Watch pullback area around {pullback_level} and look for rejection/hold before adding risk.")
    elif "risk" in q or "stop" in q or "invalidation" in q or "size" in q:
        lines.append(f"Bias: {rec.upper()} (score {score if score is not None else 'N/A'}).")
        lines.append(f"Primary risk lens: ATR={vol.get('atr', 'N/A')} and volatility regime={vol.get('volatility_regime_label', 'N/A')}.")
        lines.append("If volatility expands, reduce size first; only widen stop if setup quality improves.")
        if size_hint:
            lines.append(f"Current sizing hint: {size_hint}.")
        if pullback_level:
            lines.append(f"Practical invalidation reference: loss of structure around the pullback zone near {pullback_level}.")
    elif "trigger" in q or "confirm" in q or "break" in q:
        lines.append(f"Entry trigger view: {rec.upper()} bias (score {score if score is not None else 'N/A'}).")
        lines.append("Confirmation checklist: structure hold, momentum follow-through, and no immediate rejection after trigger.")
        if rec == "neutral":
            lines.append("No entry while neutral; wait for a confirmed break + follow-through candle before considering size.")
        if blowoff.get("applicable"):
            lines.append(
                f"Blow-off context: phase={blowoff.get('phase', 'normal')}, "
                f"state={blowoff.get('entryState') or blowoff.get('entry_state', 'wait')} — wait for structure validation."
            )
    else:
        lines.append(f"Bias: {rec.upper()} (score {score if score is not None else 'N/A'}).")
        lines.append(f"Main drivers in the current snapshot: {reason_text}.")
        lines.append("If you want, ask me for one of these: entry trigger, invalidation level, or position sizing plan.")

    return "\n".join(lines)


def _invoke_bedrock(
    question: str,
    model_id: str,
    strategy_mode: str,
    intent: str,
    context: Dict[str, Any],
    history: List[ChatMessage],
) -> Tuple[str, ChatUsage]:
    try:
        import boto3
    except Exception as exc:
        raise RuntimeError(f"boto3 unavailable: {exc}")

    region = os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
    client = boto3.client("bedrock-runtime", region_name=region)

    system_prompt = (
        "You are NEXUS Copilot, a trading analysis assistant. "
        "Use ONLY provided analysis context. Be concise, practical, and risk-aware. "
        "Never promise outcomes, never use certainty language, and never give financial guarantees. "
        "If data is missing, say what is missing. "
        "Answer the exact question directly with instrument-specific details. "
        "Do not add generic disclaimer lines unless the user explicitly asks for policy/safety framing."
    )

    safe_history = [
        {"role": m.role, "content": [{"type": "text", "text": m.content[:1200]}]}
        for m in history[-6:]
    ]

    context_blob = json.dumps(context, default=str)[:7000]
    user_text = (
        f"Intent: {intent}\n"
        f"StrategyMode: {strategy_mode}\n"
        f"AnalysisContext: {context_blob}\n"
        f"UserQuestion: {question}"
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 550,
        "temperature": 0.2,
        "system": system_prompt,
        "messages": [*safe_history, {"role": "user", "content": [{"type": "text", "text": user_text}]}],
    }

    response = client.invoke_model(modelId=model_id, body=json.dumps(payload))
    body = json.loads(response["body"].read())

    text_chunks = [c.get("text", "") for c in body.get("content", []) if c.get("type") == "text"]
    answer = "\n".join([t.strip() for t in text_chunks if t.strip()]).strip()
    if not answer:
        answer = "I could not derive a reliable answer from the current context."

    usage_raw = body.get("usage", {})
    usage = ChatUsage(
        inputTokens=int(usage_raw.get("input_tokens", usage_raw.get("inputTokens", 0)) or 0),
        outputTokens=int(usage_raw.get("output_tokens", usage_raw.get("outputTokens", 0)) or 0),
        estimatedCostUsd=0.0,
    )
    return answer, usage


@router.get("/health")
def chat_health() -> Dict[str, str]:
    return {"status": "ok", "service": "ai-chat"}


@router.post("", response_model=ChatResponse)
def chat_with_copilot(payload: ChatRequest, user_id: str = Depends(get_current_user)) -> ChatResponse:
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty")

    model_id, escalated = _select_model(payload.question, payload.intent)
    citations = _build_context_citations(payload.analysisContext)

    try:
        answer, usage = _invoke_bedrock(
            question=payload.question,
            model_id=model_id,
            strategy_mode=payload.strategyMode,
            intent=payload.intent,
            context=payload.analysisContext,
            history=payload.history,
        )
        return ChatResponse(
            answer=answer,
            modelUsed=model_id,
            escalated=escalated,
            citations=citations,
            usage=usage,
        )
    except Exception as exc:
        logger.warning("Bedrock chat unavailable for %s: %s", user_id, exc)
        fallback_answer = _fallback_answer(
            question=payload.question,
            ctx=payload.analysisContext,
            strategy_mode=payload.strategyMode,
        )
        return ChatResponse(
            answer=fallback_answer,
            modelUsed="fallback-context-only",
            escalated=False,
            citations=citations,
            usage=ChatUsage(),
        )
