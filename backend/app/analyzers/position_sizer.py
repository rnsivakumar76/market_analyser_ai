from typing import List, Dict, Any
from ..models import InstrumentAnalysis, PositionSizing, StrategySettings, Signal
import logging

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

        # ── Correlation Penalty ───────────────────────────────────────────
        avg_correlation = 0.0
        others = [s for s in trade_worthy_symbols if s != symbol]

        if others and correlation_data and correlation_data.get('labels'):
            labels = correlation_data['labels']
            matrix = correlation_data['matrix']
            if symbol in labels:
                s_idx = labels.index(symbol)
                corrs = []
                for other in others:
                    if other in labels:
                        o_idx = labels.index(other)
                        corrs.append(float(matrix[s_idx][o_idx]))
                if corrs:
                    avg_correlation = sum(corrs) / len(corrs)

        # Penalty: 0% at corr=0.3, capped at 60% reduction at corr≥0.9
        penalty_factor = 0.0
        if avg_correlation > 0.3:
            penalty_factor = min(0.6, (avg_correlation - 0.3) * 1.0)

        final_risk_percent = base_risk_percent * (1.0 - penalty_factor)
        adjusted_risk_amount = portfolio * (final_risk_percent / 100.0)

        suggested_units = adjusted_risk_amount / risk_per_unit

        # Round to a sensible precision
        if suggested_units >= 100:
            suggested_units = round(suggested_units)
        elif suggested_units >= 10:
            suggested_units = round(suggested_units, 1)
        else:
            suggested_units = round(suggested_units, 2)

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
