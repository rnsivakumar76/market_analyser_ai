---
description: Ensure pyramid opportunities stay in sync with computation logic changes
---

# Pyramid Sync Rule

**Purpose**: When fixing or updating computation-related logic (indicators, divergence detection, signal generation), ensure the pyramid opportunities screen is also updated to reflect these changes.

## When to Apply This Rule

Apply this rule whenever you modify:
- Indicator calculations (RSI, MACD, ATR, Moving Averages)
- Divergence detection logic (RSI, MACD, price-MA)
- Signal generation or confidence scoring
- Swing reversal analyzer logic
- Volatility calculations
- Multi-timeframe confirmation logic

## Files to Check and Update

When modifying computation logic, verify and update these related files:

### Backend Files:
1. **`backend/app/analyzers/swing_reversal_analyzer.py`** - Primary computation logic
2. **`backend/app/analyzers/pyramid_calculator.py`** - Pyramid level calculations
3. **`backend/app/main.py`** - `/api/pyramid/opportunities` endpoint
4. **`backend/app/models.py`** - Pydantic models if data structures change

### Frontend Files:
1. **`frontend/src/app/components/pyramid-manager/pyramid-manager.component.ts`** - Opportunity display logic
2. **`frontend/src/app/components/pyramid-manager/pyramid-manager.component.html`** - UI templates if fields change
3. **`frontend/src/app/components/pyramid-manager/pyramid-manager.component.scss`** - Styling if needed

## Checklist

Before committing computation logic changes:

- [ ] Did the change affect divergence detection? → Update pyramid opportunity confidence calculation
- [ ] Did the change affect ATR calculation? → Update pyramid level price targets and stop losses
- [ ] Did the change affect signal confidence? → Update pyramid opportunity filtering threshold
- [ ] Did the change add new signal sources? → Update pyramid opportunity divergence sources display
- [ ] Did the change modify multi-timeframe logic? → Update pyramid opportunity MTF confirmation display
- [ ] Did the change affect risk/reward calculations? → Update pyramid plan R/R ratio display

## Example Scenarios

### Scenario 1: Updating RSI Divergence Logic
If you modify `_detect_rsi_divergence` in `swing_reversal_analyzer.py`:
1. Check if confidence scoring changed
2. Update pyramid opportunity filtering in `/api/pyramid/opportunities` endpoint
3. Verify divergence source tags still display correctly in pyramid UI

### Scenario 2: Changing ATR Calculation Method
If you modify ATR calculation in `volatility_analyzer.py`:
1. Update pyramid level price targets in `pyramid_calculator.py`
2. Update stop loss calculations (2x ATR, 0.5x ATR trailing)
3. Update entry range calculation (±0.5 ATR)
4. Verify pyramid plan R/R ratios are still accurate

### Scenario 3: Adding New Divergence Type
If you add a new divergence detection (e.g., volume divergence):
1. Add to divergence sources in pyramid opportunity response
2. Update pyramid UI to display new source tag
3. Consider if new source affects confidence scoring

## Testing

After making computation logic changes:
1. Test the `/api/pyramid/opportunities` endpoint
2. Verify opportunity cards display correctly
3. Check that pyramid plans calculate accurately
4. Ensure R/R ratios are reasonable
5. Test creating a position from an opportunity

## Notes

- The pyramid opportunities endpoint (`/api/pyramid/opportunities`) directly uses the swing reversal analyzer
- Pyramid calculator uses ATR for all price-based calculations
- Any change to signal confidence affects which opportunities are shown (threshold: 60%)
- Frontend displays all data returned by the backend - ensure API response structure is consistent
