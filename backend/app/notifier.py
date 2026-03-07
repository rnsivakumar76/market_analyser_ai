import requests
import logging
import smtplib
from email.message import EmailMessage
from typing import Dict, Any, List
from .models import InstrumentAnalysis, Signal

logger = logging.getLogger(__name__)

def send_expert_alert(analysis: InstrumentAnalysis, config: Dict[str, Any]):
    """Send Expert Battle Plan to Telegram whenever a new ORB/plan is available."""
    expert_plan = analysis.expert_trade_plan
    if not expert_plan:
        return

    symbol = analysis.symbol
    price = analysis.current_price
    or_broken = expert_plan.get('or_broken', 'none')
    rvol = expert_plan.get('rvol', 1.0)
    battle_plan = expert_plan.get('battle_plan', '')
    is_high_intent = expert_plan.get('is_high_intent', False)

    if or_broken == 'bullish':
        emoji = "⚡"
        direction = "ORB BREAKOUT (BULLISH)"
    elif or_broken == 'bearish':
        emoji = "🔻"
        direction = "ORB BREAKDOWN (BEARISH)"
    else:
        emoji = "⏸"
        direction = "CONSOLIDATING (RANGE)"

    intent_flag = "  🔥 HIGH INTENT" if is_high_intent else ""
    message = (
        f"{emoji} *EXPERT BATTLE PLAN: {symbol}*{intent_flag}\n"
        f"*Price:* ${price}  |  *RVOL:* {rvol:.1f}x\n"
        f"*Status:* {direction}\n\n"
        f"{battle_plan}"
    )

    tg_config = config.get('telegram', {})
    if tg_config.get('enabled'):
        try:
            token = tg_config.get('bot_token')
            chat_id = tg_config.get('chat_id')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
            logger.info(f"Telegram expert alert sent for {symbol}")
        except Exception as e:
            logger.error(f"Failed to send Telegram expert alert: {e}")


def send_alerts(analysis: InstrumentAnalysis, config: Dict[str, Any]):
    """Send alerts if the signal is trade worthy."""
    if not analysis.trade_signal.trade_worthy:
        return

    # Trigger only for high conviction setups (Score >= 70 or user specified 100/100 logic)
    # The user mentioned "100/100", so let's trigger for any trade_worthy (which is 70+ in our code)
    
    score = analysis.trade_signal.score
    symbol = analysis.symbol
    price = analysis.current_price
    rec = analysis.trade_signal.recommendation.upper()
    
    # Format message
    emoji = "🚀" if rec == "BULLISH" else "🔻"
    message = (
        f"{emoji} *NEW TRADE SIGNAL: {symbol}*\n"
        f"*Signal:* {rec} (Score: {score}/100)\n"
        f"*Price:* ${price}\n\n"
        f"*Reasons:*\n"
    )
    for reason in analysis.trade_signal.reasons:
        message += f"• {reason}\n"
        
    message += f"\n*Probability:* {analysis.backtest_results.win_rate}% Win Rate historical"
    if analysis.candle_patterns.pattern != "none":
        message += f"\n*Trigger:* {analysis.candle_patterns.pattern.replace('_', ' ').title()}"

    # Telegram
    tg_config = config.get('telegram', {})
    if tg_config.get('enabled'):
        try:
            token = tg_config.get('bot_token')
            chat_id = tg_config.get('chat_id')
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            requests.post(url, json=payload, timeout=5)
            logger.info(f"Telegram alert sent for {symbol}")
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

    # Discord
    dc_config = config.get('discord', {})
    if dc_config.get('enabled'):
        try:
            webhook_url = dc_config.get('webhook_url')
            # Discord uses slightly different markdown for bold/italics in some cases but *bold* works fine
            payload = {
                "content": message.replace('*', '**') # Discord prefers ** for bold
            }
            requests.post(webhook_url, json=payload, timeout=5)
            logger.info(f"Discord alert sent for {symbol}")
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")

    # Email (SMTP)
    email_config = config.get('email', {})
    if email_config.get('enabled'):
        try:
            # Requires these keys in the config: smtp_server, smtp_port, username, password, to_email
            smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = email_config.get('smtp_port', 587)
            username = email_config.get('username')
            password = email_config.get('password')
            to_email = email_config.get('to_email')
            from_email = email_config.get('from_email', username)

            msg = EmailMessage()
            msg.set_content(message)
            msg['Subject'] = f"MARKET ANALYZER ALERT: {rec} on {symbol}"
            msg['From'] = from_email
            msg['To'] = to_email

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent for {symbol} to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send Email alert: {e}")
