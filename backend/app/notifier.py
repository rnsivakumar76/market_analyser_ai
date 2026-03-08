import requests
import logging
import smtplib
from email.message import EmailMessage
from typing import Dict, Any, List
from .models import InstrumentAnalysis, Signal

logger = logging.getLogger(__name__)

def send_expert_alert(analysis: InstrumentAnalysis, config: Dict[str, Any]):
    """Send Expert Battle Plan to Telegram for confirmed ORB breakouts only.

    Suppressed when:
    - or_broken == 'none'  (still consolidating — not actionable)
    - is_high_intent == False  (low RVOL / weak conviction setup)
    This prevents a flood of 'consolidating' notifications on every scan cycle.
    """
    expert_plan = analysis.expert_trade_plan
    if not expert_plan:
        return

    or_broken = expert_plan.get('or_broken', 'none')
    is_high_intent = expert_plan.get('is_high_intent', False)

    # Only notify on actual directional ORB breaks with high intent
    if or_broken == 'none' or not is_high_intent:
        return

    symbol = analysis.symbol
    price = analysis.current_price
    rvol = expert_plan.get('rvol', 1.0)
    battle_plan = expert_plan.get('battle_plan', '')

    emoji = "⚡" if or_broken == 'bullish' else "🔻"
    direction = "ORB BREAKOUT — BULLISH" if or_broken == 'bullish' else "ORB BREAKDOWN — BEARISH"

    message = (
        f"{emoji} *ORB ALERT: {symbol}* 🔥 HIGH INTENT\n"
        f"*{direction}*\n"
        f"*Price:* ${price}  |  *RVOL:* {rvol:.1f}×\n\n"
        f"{battle_plan}"
    )

    tg_config = config.get('telegram', {})
    if tg_config.get('enabled'):
        try:
            token = tg_config.get('bot_token')
            chat_id = tg_config.get('chat_id')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
            logger.info(f"Telegram expert alert sent for {symbol} ({direction})")
        except Exception as e:
            logger.error(f"Failed to send Telegram expert alert: {e}")


def _fmt_price(price: float, symbol: str = '') -> str:
    """Format price with appropriate decimal places."""
    if price is None:
        return 'N/A'
    sym = symbol.upper()
    if any(x in sym for x in ['BTC', 'ETH']):
        return f"${price:,.0f}"
    if any(x in sym for x in ['XAU', 'GOLD']):
        return f"${price:,.2f}"
    return f"${price:.2f}"


def _build_signal_message(analysis: InstrumentAnalysis) -> str:
    """Build a rich, actionable Telegram/Discord trade signal message."""
    sig   = analysis.trade_signal
    vol   = analysis.volatility_risk
    candle = analysis.candle_patterns
    bt    = analysis.backtest_results
    news  = analysis.news_sentiment
    geo   = getattr(analysis, 'geopolitical_risk', None)
    ps    = analysis.position_sizing  # may be None
    mode  = getattr(analysis, 'strategy_mode', None)

    symbol  = analysis.symbol
    price   = analysis.current_price
    score   = sig.score
    rec     = sig.recommendation.value.upper() if hasattr(sig.recommendation, 'value') else str(sig.recommendation).upper()
    emoji   = "🚀" if rec == 'BULLISH' else "🔻"
    mode_tag = f" [{str(mode.value).replace('_', ' ')}]" if mode else ""

    # ── Entry / exit levels ────────────────────────────────────────────────────
    entry = ps.entry_price if ps else price
    sl    = ps.stop_loss   if ps else (vol.stop_loss   if vol else None)
    tp1   = vol.take_profit_level1 if vol else None
    tp2   = vol.take_profit_level2 if vol else None
    tp    = ps.take_profit if ps else (vol.take_profit  if vol else None)
    rr    = vol.risk_reward_ratio   if vol else None
    atr   = vol.atr                 if vol else None
    atr_regime = getattr(vol, 'atr_regime', '') if vol else ''

    entry_section = f"\n📍 *ENTRY / EXIT PLAN*\n"
    entry_section += f"*Entry:*     {_fmt_price(entry, symbol)} (market)\n"
    if sl:
        entry_section += f"*Stop Loss:* {_fmt_price(sl, symbol)}"
        if atr:
            entry_section += f"  (–{abs(entry - sl) / atr:.1f} ATR)"
        entry_section += "\n"
    if tp1:
        entry_section += f"*Target 1:*  {_fmt_price(tp1, symbol)}  (partial — scale out)\n"
    if tp2:
        entry_section += f"*Target 2:*  {_fmt_price(tp2, symbol)}  (full target)\n"
    elif tp:
        entry_section += f"*Target:*    {_fmt_price(tp, symbol)}\n"
    if rr:
        entry_section += f"*R/R Ratio:* 1 : {rr:.1f}\n"
    if atr:
        entry_section += f"*ATR:*       {_fmt_price(atr, symbol)}"
        if atr_regime and atr_regime != 'NORMAL':
            entry_section += f"  ({atr_regime})"
        entry_section += "\n"

    # ── Signal support (top 4 reasons, strip long score suffixes for readability) ─
    support_section = "\n📊 *SIGNAL SUPPORT*\n"
    top_reasons = sig.reasons[:5]
    for r in top_reasons:
        support_section += f"• {r}\n"

    # ── News / geo context ─────────────────────────────────────────────────────
    context_parts: List[str] = []
    if news:
        context_parts.append(f"News: {news.label}")
    if geo and geo.detected and geo.risk_level not in ('NONE', 'LOW'):
        cats = ', '.join(geo.event_categories[:2]) if geo.event_categories else ''
        context_parts.append(f"Geo Risk: {geo.risk_level} ({cats})" if cats else f"Geo Risk: {geo.risk_level}")
    context_section = ""
    if context_parts:
        context_section = "\n📰 *CONTEXT*\n" + "  |  ".join(context_parts) + "\n"

    # ── Trigger candle ─────────────────────────────────────────────────────────
    candle_str = ""
    if candle and candle.pattern and candle.pattern.lower() not in ('none', ''):
        candle_str = f"\n*Trigger:* {candle.pattern.replace('_', ' ').title()}"

    # ── Historical edge ────────────────────────────────────────────────────────
    edge_section = ""
    if bt:
        edge_section = f"\n📈 *HISTORICAL EDGE*\nWin Rate: {bt.win_rate}%{candle_str}\n"

    # ── Position sizing hint ───────────────────────────────────────────────────
    ps_section = ""
    if ps and ps.suggested_units and ps.risk_amount:
        ps_section = (
            f"\n� *SIZING*\n"
            f"Units: {ps.suggested_units:.2f}  |  Risk: {_fmt_price(ps.risk_amount, symbol)}  ({ps.final_risk_percent:.1f}% of portfolio)\n"
        )

    header = (
        f"{emoji} *TRADE SIGNAL — {symbol}*{mode_tag}\n"
        f"*Signal:* {rec}  |  Score: {score}/100\n"
        f"*Price:* {_fmt_price(price, symbol)}\n"
    )

    return header + entry_section + support_section + context_section + edge_section + ps_section


def send_alerts(analysis: InstrumentAnalysis, config: Dict[str, Any]):
    """Send trade signal alert with entry/exit plan, R/R, and supporting data."""
    if not analysis.trade_signal.trade_worthy:
        return

    message = _build_signal_message(analysis)
    symbol  = analysis.symbol
    rec     = analysis.trade_signal.recommendation.value.upper() if hasattr(analysis.trade_signal.recommendation, 'value') else str(analysis.trade_signal.recommendation).upper()

    # Telegram
    tg_config = config.get('telegram', {})
    if tg_config.get('enabled'):
        try:
            token = tg_config.get('bot_token')
            chat_id = tg_config.get('chat_id')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
            logger.info(f"Telegram alert sent for {symbol}")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

    # Discord
    dc_config = config.get('discord', {})
    if dc_config.get('enabled'):
        try:
            webhook_url = dc_config.get('webhook_url')
            payload = {"content": message.replace('*', '**')}
            requests.post(webhook_url, json=payload, timeout=5)
            logger.info(f"Discord alert sent for {symbol}")
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")

    # Email (SMTP)
    email_config = config.get('email', {})
    if email_config.get('enabled'):
        try:
            smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port   = email_config.get('smtp_port', 587)
            username    = email_config.get('username')
            password    = email_config.get('password')
            to_email    = email_config.get('to_email')
            from_email  = email_config.get('from_email', username)

            msg = EmailMessage()
            msg.set_content(message)
            msg['Subject'] = f"TRADE SIGNAL: {rec} on {symbol}"
            msg['From']    = from_email
            msg['To']      = to_email

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
            logger.info(f"Email alert sent for {symbol} to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send Email alert: {e}")
