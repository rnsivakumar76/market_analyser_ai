import requests
import logging
from typing import Dict, Any, List
from .models import InstrumentAnalysis, Signal

logger = logging.getLogger(__name__)

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
