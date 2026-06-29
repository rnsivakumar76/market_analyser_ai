"""
Pyramid Position Calculator (Analyzer Layer)
──────────────────────────────────────────
Implements Jesse Livermore's pyramid technique for position management.
Calculates when to add positions, stop loss adjustments, and risk/reward.
"""

from typing import List, Dict, Optional
from app.models import (
    PyramidPosition,
    PyramidRecommendation,
    PyramidLevel,
    PyramidPlan
)


def calculate_pyramid_plan(
    position: PyramidPosition,
    atr: float,
    current_price: float,
    trading_style: str = "swing"  # 'swing' or 'day'
) -> PyramidPlan:
    """
    Calculate complete pyramid plan for a position using Livermore's technique.
    
    Livermore's Pyramid Rules:
    1. Start with small base position (20% of total planned size)
    2. Add only when price moves favorably by at least 1x ATR
    3. Each addition is larger than previous (pyramid shape)
    4. Move stop loss to break-even after first successful addition
    5. Trail stop loss by 0.5x ATR after each addition
    6. Never add more than 5 levels total
    7. Take partial profits at peak level
    
    Trading Styles:
    - Swing: Standard multipliers, 5 levels, 1.5x ATR increments (longer timeframe)
    - Day: Tighter multipliers, 3 levels, 0.5x ATR increments (faster completion)
    
    Args:
        position: Current position details
        atr: Average True Range for volatility measurement
        current_price: Current market price
        trading_style: 'swing' for swing trading, 'day' for day trading
        
    Returns:
        Complete pyramid plan with levels and recommendations
    """
    direction = position.direction
    entry_price = position.entry_price
    initial_lots = position.initial_lots
    
    # Configure based on trading style
    if trading_style == "day":
        max_levels = 3
        price_increment_mult = 0.5  # Smaller increments for day trading
        trail_distance_mult = 0.3  # Tighter trailing stops
    else:  # swing (default)
        max_levels = 5
        price_increment_mult = 1.5
        trail_distance_mult = 0.5
    
    # Calculate pyramid levels
    levels = _generate_pyramid_levels(
        direction=direction,
        entry_price=entry_price,
        initial_lots=initial_lots,
        atr=atr,
        max_levels=max_levels,
        price_increment_mult=price_increment_mult,
        trail_distance_mult=trail_distance_mult
    )
    
    # Determine current level based on current price
    current_level = _determine_current_level(
        direction=direction,
        current_price=current_price,
        levels=levels
    )
    
    # Generate current recommendation
    recommendation = _generate_recommendation(
        position=position,
        current_level=current_level,
        levels=levels,
        current_price=current_price,
        atr=atr
    )
    
    # Calculate total risk and reward
    total_risk, total_reward = _calculate_risk_reward(
        position=position,
        levels=levels,
        current_level=current_level
    )
    
    return PyramidPlan(
        position_id=position.id,
        symbol=position.symbol,
        direction=direction,
        current_level=current_level,
        max_levels=5,
        levels=levels,
        current_recommendation=recommendation,
        total_risk=total_risk,
        total_reward=total_reward,
        overall_risk_reward=total_reward / total_risk if total_risk > 0 else 0
    )


def _generate_pyramid_levels(
    direction: str,
    entry_price: float,
    initial_lots: int,
    atr: float,
    max_levels: int = 5,
    price_increment_mult: float = 1.5,
    trail_distance_mult: float = 0.5
) -> List[PyramidLevel]:
    """Generate pyramid levels with price targets and lot additions."""
    levels = []
    cumulative_lots = initial_lots
    
    # Base level (entry)
    levels.append(PyramidLevel(
        level=1,
        price_target=entry_price,
        lots_to_add=initial_lots,
        cumulative_lots=cumulative_lots,
        stop_loss_adjustment=entry_price - (2 * atr) if direction == 'long' else entry_price + (2 * atr),
        description="Base position - initial entry"
    ))
    
    # Build pyramid levels (2-max_levels)
    for i in range(2, max_levels + 1):
        # Calculate price target using dynamic multiplier
        price_increment = atr * price_increment_mult
        if direction == 'long':
            price_target = entry_price + (price_increment * (i - 1))
        else:
            price_target = entry_price - (price_increment * (i - 1))
        
        # Calculate lots to add (pyramid: each level adds more)
        # Adjust percentages based on max_levels
        if max_levels == 3:
            add_percentages = [0.35, 0.40]  # Day trading: fewer levels, larger additions
        else:
            add_percentages = [0.25, 0.30, 0.35, 0.40]  # Swing trading
        
        lots_to_add = int(initial_lots * add_percentages[i - 2])
        cumulative_lots += lots_to_add
        
        # Calculate stop loss adjustment using dynamic trail distance
        # After level 2, move to break-even
        # After level 3+, trail by configured multiplier
        if i == 2:
            sl_adjustment = entry_price  # Break-even
        elif i >= 3:
            trail_distance = atr * trail_distance_mult
            if direction == 'long':
                sl_adjustment = price_target - trail_distance
            else:
                sl_adjustment = price_target + trail_distance
        else:
            sl_adjustment = entry_price - (2 * atr) if direction == 'long' else entry_price + (2 * atr)
        
        stage_names = ["BUILD_1", "BUILD_2", "BUILD_3", "PEAK"]
        description = f"{stage_names[i-2]} - Add {lots_to_add} lots at {price_target:.2f}"
        
        levels.append(PyramidLevel(
            level=i,
            price_target=price_target,
            lots_to_add=lots_to_add,
            cumulative_lots=cumulative_lots,
            stop_loss_adjustment=sl_adjustment,
            description=description
        ))
    
    return levels


def _determine_current_level(
    direction: str,
    current_price: float,
    levels: List[PyramidLevel]
) -> int:
    """Determine which pyramid level the current price is at."""
    for i, level in enumerate(levels):
        if direction == 'long':
            if current_price >= level.price_target:
                current_level = level.level
            else:
                break
        else:  # short
            if current_price <= level.price_target:
                current_level = level.level
            else:
                break
    
    return current_level if 'current_level' in locals() else 1


def _generate_recommendation(
    position: PyramidPosition,
    current_level: int,
    levels: List[PyramidLevel],
    current_price: float,
    atr: float
) -> PyramidRecommendation:
    """Generate current recommendation based on pyramid level."""
    max_level = len(levels)
    direction = position.direction
    
    # If at max level, recommend partial exit
    if current_level >= max_level:
        return PyramidRecommendation(
            position_id=position.id,
            action="PARTIAL_EXIT",
            current_price=current_price,
            new_stop_loss=levels[-1].stop_loss_adjustment,
            reason="At pyramid peak - take partial profits",
            risk_reward=2.0,
            confidence=0.8,
            pyramid_stage="PEAK"
        )
    
    # Check if ready to add next level
    next_level = levels[current_level] if current_level < max_level else None
    if next_level:
        price_threshold = next_level.price_target
        if direction == 'long':
            ready_to_add = current_price >= price_threshold
        else:
            ready_to_add = current_price <= price_threshold
        
        if ready_to_add:
            stage_names = ["BASE", "BUILD_1", "BUILD_2", "BUILD_3", "PEAK"]
            return PyramidRecommendation(
                position_id=position.id,
                action="ADD_POSITION",
                current_price=current_price,
                target_add_price=next_level.price_target,
                target_add_lots=next_level.lots_to_add,
                new_stop_loss=next_level.stop_loss_adjustment,
                reason=f"Price reached level {current_level + 1} target - add {next_level.lots_to_add} lots",
                risk_reward=1.5,
                confidence=0.7,
                pyramid_stage=stage_names[current_level]
            )
    
    # Check if stop loss needs adjustment
    current_sl = position.current_stop_loss
    recommended_sl = levels[current_level - 1].stop_loss_adjustment
    
    sl_diff = abs(recommended_sl - current_sl)
    if sl_diff > (atr * 0.3):  # Only adjust if difference is significant
        return PyramidRecommendation(
            position_id=position.id,
            action="MOVE_STOP",
            current_price=current_price,
            new_stop_loss=recommended_sl,
            reason=f"Adjust stop loss to {recommended_sl:.2f} (trailing stop)",
            risk_reward=1.0,
            confidence=0.6,
            pyramid_stage="BASE" if current_level == 1 else f"BUILD_{current_level - 1}"
        )
    
    # Default: hold
    stage_names = ["BASE", "BUILD_1", "BUILD_2", "BUILD_3", "PEAK"]
    return PyramidRecommendation(
        position_id=position.id,
        action="HOLD",
        current_price=current_price,
        reason=f"Wait for price to reach next level target",
        risk_reward=1.0,
        confidence=0.5,
        pyramid_stage=stage_names[current_level - 1]
    )


def _calculate_risk_reward(
    position: PyramidPosition,
    levels: List[PyramidLevel],
    current_level: int
) -> tuple:
    """Calculate total risk and reward for the pyramid plan."""
    direction = position.direction
    entry_price = position.entry_price
    current_lots = position.current_lots
    
    # Risk: distance from current price to stop loss
    current_sl = levels[current_level - 1].stop_loss_adjustment
    if direction == 'long':
        risk_per_lot = max(0, position.current_price - current_sl)
    else:
        risk_per_lot = max(0, current_sl - position.current_price)
    
    total_risk = risk_per_lot * current_lots
    
    # Reward: distance to final target (peak level)
    final_target = levels[-1].price_target
    if direction == 'long':
        reward_per_lot = final_target - position.current_price
    else:
        reward_per_lot = position.current_price - final_target
    
    total_reward = reward_per_lot * current_lots
    
    return total_risk, total_reward
