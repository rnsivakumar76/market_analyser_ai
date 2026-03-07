from typing import List, Dict, Any
from ..models import InstrumentAnalysis, PositionSizing, StrategySettings, Signal
import logging
from domain.trading.position_sizer import (
    calculate_correlation_penalty,
    calculate_risk_per_unit,
    calculate_position_units as _domain_size,
)

logger = logging.getLogger(__name__)


def apply_position_sizing(
    results: List[InstrumentAnalysis],
    correlation_data: Dict[str, Any],
    settings: StrategySettings
) -> List[InstrumentAnalysis]:
    """
    Calculate risk-adjusted position sizes for ALL instruments, regardless of trade signal.
    This gives the user sizing info even when the market is mixed/uncertain.
    """
    if not settings:
        logger.warning("No settings provided to position sizer, skipping.")
        return results

    portfolio = float(settings.portfolio_value)
    base_risk_percent = float(settings.risk_per_trade_percent)

    if portfolio <= 0 or base_risk_percent <= 0:
        logger.warning("Invalid portfolio value or risk percent.")
        return results

    # Symbols that have a non-neutral AND trade-worthy signal (used for correlation penalty)
    trade_worthy_symbols = [
        r.symbol for r in results
        if r.trade_signal.trade_worthy
    ]

    logger.info(f"Position sizing: portfolio=${portfolio}, risk={base_risk_percent}%, "
                f"trade-worthy instruments: {trade_worthy_symbols}")

    for idx, analysis in enumerate(results):
        symbol = analysis.symbol

        # Skip if no volatility data
        if not analysis.volatility_risk:
            logger.warning(f"[{symbol}] Skipping — no volatility data")
            continue

        atr = float(analysis.volatility_risk.atr) if analysis.volatility_risk.atr else 0.0
        if atr <= 0:
            logger.warning(f"[{symbol}] Skipping — ATR is 0")
            continue

        entry = float(analysis.current_price)
        sl = float(analysis.volatility_risk.stop_loss)
        tp = float(analysis.volatility_risk.take_profit)

        risk_per_unit = abs(entry - sl)

        # Fallback: if SL = entry (shouldn't happen but guard it), use 1.5x ATR
        if risk_per_unit < 0.0001:
            risk_per_unit = atr * 1.5
            sl = entry - risk_per_unit  # assume long
            logger.warning(f"[{symbol}] SL equals entry, using ATR fallback for risk_per_unit={risk_per_unit:.4f}")

        # ── Correlation Penalty (domain layer) ───────────────────────────
        avg_correlation = 0.0
        others = [s for s in trade_worthy_symbols if s != symbol]

        if others and correlation_data and correlation_data.get('labels'):
            labels = correlation_data['labels']
            matrix = correlation_data['matrix']
            if symbol in labels:
                s_idx = labels.index(symbol)
                corrs = [
                    float(matrix[s_idx][labels.index(other)])
                    for other in others if other in labels
                ]
                if corrs:
                    avg_correlation = sum(corrs) / len(corrs)

        # ── Domain layer: sizing ─────────────────────────────────────────
        suggested_units, adjusted_risk_amount, penalty_factor, final_risk_percent = _domain_size(
            portfolio_value=portfolio,
            base_risk_percent=base_risk_percent,
            entry_price=entry,
            stop_loss=sl,
            atr=atr,
            avg_correlation=avg_correlation,
        )

        # Build description
        desc = f"Risk {final_risk_percent:.1f}% of portfolio (${adjusted_risk_amount:.0f}). "
        if penalty_factor > 0:
            desc += (f"Size reduced by {penalty_factor*100:.0f}% due to "
                     f"high correlation ({avg_correlation:.2f}) with other active signals.")
        else:
            desc += "Full size allocated — independent signal."

        sizing = PositionSizing(
            suggested_units=float(suggested_units),
            risk_amount=round(float(adjusted_risk_amount), 2),
            entry_price=round(entry, 4),
            stop_loss=round(float(sl), 4),
            take_profit=round(float(tp), 4),
            correlation_penalty=round(penalty_factor * 100, 1),
            final_risk_percent=round(final_risk_percent, 2),
            description=desc
        )

        results[idx] = analysis.model_copy(update={"position_sizing": sizing})
        logger.info(f"[{symbol}] Sizing done: {suggested_units} units, "
                    f"risk=${adjusted_risk_amount:.2f}, corr_penalty={penalty_factor*100:.1f}%")

    return results
