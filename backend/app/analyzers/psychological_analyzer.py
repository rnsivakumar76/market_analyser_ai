import logging
from ..models import PerformanceSummary, PsychologicalGuardrail, SystemStatus

logger = logging.getLogger(__name__)

def analyze_psychological_state(performance: PerformanceSummary, daily_loss_limit: float = -2.0, max_losing_streak: int = 3) -> PsychologicalGuardrail:
    """
    Analyzes the strategy's recent performance to determine if the system should 
    enter a 'Lockdown' state to protect the user's capital and mental state.
    """
    
    current_pnl = performance.total_pnl_percent
    # Simplified logic: If total PnL is significantly negative, or we see a bad worst trade
    # in an actual production app, this would use a real-time account balance.
    
    status = SystemStatus.ACTIVE
    reason = ""
    message = "🧠 Discipline Protocol: Active. Trade your plan."
    
    # Check for Daily/Weekly Loss Limit
    if current_pnl <= daily_loss_limit:
        status = SystemStatus.RESTRICTED
        reason = f"Loss Limit Reached ({current_pnl:.2f}%)"
        message = f"🛡️ SYSTEM LOCKDOWN: You have reached your max loss limit of {daily_loss_limit}%. Trading restricted to prevent emotional decisions and further drawdown."
    
    # Check for excessive losing streak proxy
    # In this simulated environment, we check if win rate is dangerously low (< 20%)
    elif performance.total_trades >= 3 and performance.win_rate < 20:
        status = SystemStatus.RESTRICTED
        reason = "losing_streak"
        message = "🛡️ SYSTEM LOCKDOWN: High failure rate detected. The current market regime is not respecting our edge. Stop trading to protect your equity."

    return PsychologicalGuardrail(
        status=status,
        daily_pnl=current_pnl,
        daily_loss_limit=daily_loss_limit,
        consecutive_losses=3 if performance.win_rate < 20 else 0, # Placeholder
        max_consecutive_losses=max_losing_streak,
        lockdown_reason=reason,
        message=message
    )
