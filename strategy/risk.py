import math
import logging
from typing import Optional, Dict, List
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def position_size(equity_usdt: float, entry_price: float, stop_price: float, 
                 risk_pct: float, lot_step: float) -> float:
    """
    Calculate position size based on risk percentage
    
    Args:
        equity_usdt: Current account equity in USDT
        entry_price: Entry price for the trade
        stop_price: Stop loss price
        risk_pct: Risk percentage (0.01 = 1%)
        lot_step: Minimum lot size step (e.g., 0.001 for SOL)
    
    Returns:
        float: Position quantity rounded to lot_step
    
    Example:
        equity=10k, risk=0.5%, entry=150, sl=145 → qty≈10 SOL
    """
    try:
        # Validate inputs
        if equity_usdt <= 0:
            logger.error("Equity must be positive")
            return 0.0
        
        if entry_price <= 0:
            logger.error("Entry price must be positive")
            return 0.0
        
        if stop_price <= 0:
            logger.error("Stop price must be positive")
            return 0.0
        
        if risk_pct <= 0 or risk_pct > 1:
            logger.error("Risk percentage must be between 0 and 1")
            return 0.0
        
        if lot_step <= 0:
            logger.error("Lot step must be positive")
            return 0.0
        
        # Calculate risk amount in USDT
        risk_amount_usdt = equity_usdt * risk_pct
        
        # Calculate price difference (risk per unit)
        price_diff = abs(entry_price - stop_price)
        
        if price_diff == 0:
            logger.error("Entry and stop prices cannot be the same")
            return 0.0
        
        # Calculate position size
        position_qty = risk_amount_usdt / price_diff
        
        # Round down to lot step
        rounded_qty = math.floor(position_qty / lot_step) * lot_step
        
        # Ensure minimum position size
        if rounded_qty < lot_step:
            logger.warning(f"Calculated position size {rounded_qty} is below minimum {lot_step}")
            return 0.0
        
        logger.info(f"Position size calculated: {rounded_qty:.6f} (risk: ${risk_amount_usdt:.2f})")
        return rounded_qty
        
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return 0.0


def daily_guardrails(trades_today: int, pnl_today: float, stop_pct: float, 
                    start_equity: float) -> bool:
    """
    Check if trading should continue based on daily limits
    
    Args:
        trades_today: Number of trades executed today
        pnl_today: Today's P&L in USDT
        stop_pct: Daily loss stop percentage (0.01 = 1%)
        start_equity: Starting equity for the day
    
    Returns:
        bool: True if trading should continue, False if stopped
    """
    try:
        # Validate inputs
        if trades_today < 0:
            logger.error("Trades count cannot be negative")
            return False
        
        if start_equity <= 0:
            logger.error("Start equity must be positive")
            return False
        
        if stop_pct <= 0 or stop_pct > 1:
            logger.error("Stop percentage must be between 0 and 1")
            return False
        
        # Calculate daily loss limit
        daily_loss_limit = start_equity * stop_pct
        
        logger.info(f"Daily guardrails check: trades_today={trades_today}, pnl_today=${pnl_today:.2f}, start_equity=${start_equity:.2f}, daily_loss_limit=${daily_loss_limit:.2f}")
        
        # Check if daily loss limit exceeded
        if pnl_today < -daily_loss_limit:
            logger.warning(f"Daily loss limit exceeded: P&L ${pnl_today:.2f}, limit ${-daily_loss_limit:.2f}")
            return False
        
        # Check if too many trades today (optional safety measure)
        max_trades_per_day = 20  # Configurable
        if trades_today >= max_trades_per_day:
            logger.warning(f"Maximum trades per day reached: {trades_today}")
            return False
        
        logger.info(f"Daily guardrails passed: trades={trades_today}, pnl=${pnl_today:.2f}")
        return True
        
    except Exception as e:
        logger.error(f"Error checking daily guardrails: {e}")
        return False


@dataclass
class CooldownTracker:
    """Track cooldown periods between trades"""
    
    def __init__(self, cooldown_bars: int = 1):
        self.cooldown_bars = cooldown_bars
        self.last_close_bar = None
        self.bars_since_close = 0
        self.is_in_cooldown = False
    
    def update_bar(self, current_bar: int) -> None:
        """
        Update cooldown tracker with current bar
        
        Args:
            current_bar: Current bar number/timestamp
        """
        try:
            if self.last_close_bar is not None:
                self.bars_since_close = current_bar - self.last_close_bar
            else:
                # If no trade has been closed yet, we're not in cooldown
                self.bars_since_close = self.cooldown_bars
                self.is_in_cooldown = False
                logger.info(f"Cooldown: No previous trades, allowing trading")
                return
            
            # Check if cooldown period has passed
            if self.bars_since_close >= self.cooldown_bars:
                self.is_in_cooldown = False
            else:
                self.is_in_cooldown = True
                
            logger.info(f"Cooldown: bars_since_close={self.bars_since_close}, in_cooldown={self.is_in_cooldown}")
            
        except Exception as e:
            logger.error(f"Error updating cooldown tracker: {e}")
    
    def record_trade_close(self, current_bar: int) -> None:
        """
        Record when a trade is closed
        
        Args:
            current_bar: Current bar number/timestamp
        """
        try:
            self.last_close_bar = current_bar
            self.bars_since_close = 0
            self.is_in_cooldown = True
            logger.info(f"Trade closed, cooldown started at bar {current_bar}")
            
        except Exception as e:
            logger.error(f"Error recording trade close: {e}")
    
    def can_trade(self) -> bool:
        """
        Check if trading is allowed based on cooldown
        
        Returns:
            bool: True if trading is allowed
        """
        return not self.is_in_cooldown
    
    def get_cooldown_status(self) -> Dict:
        """
        Get current cooldown status
        
        Returns:
            dict: Cooldown status information
        """
        return {
            'is_in_cooldown': self.is_in_cooldown,
            'bars_since_close': self.bars_since_close,
            'cooldown_bars': self.cooldown_bars,
            'last_close_bar': self.last_close_bar
        }


class RiskManager:
    """Enhanced risk management with loss analysis insights"""
    
    def __init__(self, initial_equity: float, risk_per_trade_pct: float = 0.01, 
                 daily_loss_stop_pct: float = 0.05, cooldown_bars: int = 1):
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.risk_per_trade_pct = risk_per_trade_pct
        self.daily_loss_stop_pct = daily_loss_stop_pct
        self.cooldown_bars = cooldown_bars
        
        # NEW: Enhanced risk management based on loss analysis
        self.max_consecutive_losses = 3  # Stop after 3 consecutive losses
        self.consecutive_loss_count = 0
        self.consecutive_loss_cooldown_hours = 24
        self.last_loss_time = None
        
        # NEW: Dynamic risk adjustment
        self.base_risk_pct = risk_per_trade_pct
        self.risk_multiplier = 1.0
        self.min_risk_pct = 0.005  # Minimum 0.5% risk
        self.max_risk_pct = 0.015  # Maximum 1.5% risk
        
        # NEW: Performance tracking
        self.recent_trades = []  # Last 20 trades
        self.max_recent_trades = 20
        self.win_rate_threshold = 0.4  # 40% minimum win rate
        
        # NEW: Loss pattern analysis
        self.loss_patterns = {
            'stop_loss_hits': 0,
            'large_losses': 0,  # >2% loss
            'quick_losses': 0,  # <1 hour
            'worst_hours': [6, 7, 8, 9, 10, 11],  # 06:00-12:00
            'worst_days': ['Sunday']
        }
        
        # NEW: Market condition tracking
        self.market_volatility = 0.0
        self.trend_strength = 0.0
        self.last_signal_quality = 0.0
        
        logger.info(f"Risk manager initialized: equity=${initial_equity:.2f}, risk={risk_per_trade_pct*100}%, daily_stop={daily_loss_stop_pct*100}%")
        logger.info(f"Enhanced features: max_consecutive_losses={self.max_consecutive_losses}, cooldown={self.consecutive_loss_cooldown_hours}h")

    def update_equity(self, new_equity: float):
        """Update current equity and recalculate risk parameters"""
        self.current_equity = new_equity
        self._adjust_risk_parameters()

    def _adjust_risk_parameters(self):
        """Dynamically adjust risk parameters based on performance"""
        if len(self.recent_trades) < 5:
            return  # Need more data
        
        # Calculate current win rate
        wins = sum(1 for trade in self.recent_trades if trade.get('pnl', 0) > 0)
        win_rate = wins / len(self.recent_trades)
        
        # Calculate recent performance
        recent_pnl = sum(trade.get('pnl', 0) for trade in self.recent_trades[-5:])
        recent_performance = recent_pnl / self.initial_equity
        
        # Adjust risk based on performance
        if win_rate < self.win_rate_threshold:
            # Poor performance - reduce risk
            self.risk_multiplier = 0.5
            logger.warning(f"Low win rate ({win_rate:.1%}) - reducing risk to {self.risk_multiplier}x")
        elif recent_performance < -0.05:  # 5% recent loss
            # Recent losses - reduce risk
            self.risk_multiplier = 0.7
            logger.warning(f"Recent losses ({recent_performance:.1%}) - reducing risk to {self.risk_multiplier}x")
        elif win_rate > 0.6 and recent_performance > 0.02:
            # Good performance - can increase risk slightly
            self.risk_multiplier = 1.2
            logger.info(f"Good performance (win_rate={win_rate:.1%}, recent={recent_performance:.1%}) - increasing risk to {self.risk_multiplier}x")
        else:
            # Normal performance - standard risk
            self.risk_multiplier = 1.0
        
        # Apply risk multiplier
        adjusted_risk = self.base_risk_pct * self.risk_multiplier
        self.risk_per_trade_pct = max(self.min_risk_pct, min(adjusted_risk, self.max_risk_pct))

    def can_trade(self, signal_quality: float = 0.0, market_conditions: dict = None) -> tuple[bool, str]:
        """Enhanced trade permission check with multiple filters"""
        
        # NEW: Check consecutive loss limit
        if self.consecutive_loss_count >= self.max_consecutive_losses:
            if self.last_loss_time:
                hours_since_loss = (datetime.now() - self.last_loss_time).total_seconds() / 3600
                if hours_since_loss < self.consecutive_loss_cooldown_hours:
                    remaining = self.consecutive_loss_cooldown_hours - hours_since_loss
                    return False, f"Max consecutive losses ({self.max_consecutive_losses}) reached. Cooldown: {remaining:.1f}h remaining"
                else:
                    # Reset after cooldown
                    self.consecutive_loss_count = 0
                    logger.info("Consecutive loss cooldown completed - resuming trading")
            else:
                return False, f"Max consecutive losses ({self.max_consecutive_losses}) reached. Cooldown active"
        
        # NEW: Check signal quality
        if signal_quality < 50:  # Signal strength below 50%
            return False, f"Signal quality too low: {signal_quality:.1f}% (minimum 50%)"
        
        # NEW: Check market conditions
        if market_conditions:
            if market_conditions.get('high_volatility', False):
                return False, "Market volatility too high - avoid trading"
            if market_conditions.get('low_volume', False):
                return False, "Market volume too low - avoid trading"
        
        # NEW: Check time-based filters (from loss analysis)
        current_hour = datetime.now().hour
        if current_hour in self.loss_patterns['worst_hours']:
            return False, f"Trading hour {current_hour}:00 in worst performing period (06:00-12:00)"
        
        current_day = datetime.now().strftime('%A')
        if current_day in self.loss_patterns['worst_days']:
            return False, f"Trading day {current_day} in worst performing period"
        
        # Standard checks
        if self.current_equity <= 0:
            return False, "Insufficient equity"
        
        # Check daily loss limit
        daily_pnl = self._calculate_daily_pnl()
        if daily_pnl < -(self.current_equity * self.daily_loss_stop_pct):
            return False, f"Daily loss limit reached: ${daily_pnl:.2f}"
        
        return True, "Trading allowed"

    def calculate_position_size(self, entry_price: float, stop_loss: float, 
                              signal_quality: float = 0.0) -> float:
        """Enhanced position sizing with signal quality consideration"""
        
        # Calculate base position size
        risk_amount = self.current_equity * self.risk_per_trade_pct
        price_difference = abs(entry_price - stop_loss)
        
        if price_difference <= 0:
            logger.error("Invalid stop loss - cannot calculate position size")
            return 0.0
        
        base_position_size = risk_amount / price_difference
        
        # NEW: Adjust position size based on signal quality
        if signal_quality >= 80:
            # High quality signal - can increase position
            position_multiplier = 1.2
            logger.info(f"High signal quality ({signal_quality:.1f}%) - increasing position size by 20%")
        elif signal_quality >= 60:
            # Medium quality signal - standard position
            position_multiplier = 1.0
        else:
            # Low quality signal - reduce position
            position_multiplier = 0.7
            logger.warning(f"Low signal quality ({signal_quality:.1f}%) - reducing position size by 30%")
        
        # NEW: Adjust position size based on recent performance
        if len(self.recent_trades) >= 3:
            recent_losses = sum(1 for trade in self.recent_trades[-3:] if trade.get('pnl', 0) < 0)
            if recent_losses >= 2:
                position_multiplier *= 0.5  # Reduce position after recent losses
                logger.warning(f"Recent losses detected - reducing position size by 50%")
        
        adjusted_position_size = base_position_size * position_multiplier
        
        # NEW: Ensure position size is within limits
        max_position_value = self.current_equity * 0.15  # Max 15% of equity
        min_position_value = 1.0  # Min $1 position
        
        position_value = adjusted_position_size * entry_price
        if position_value > max_position_value:
            adjusted_position_size = max_position_value / entry_price
            logger.info(f"Position size capped at 15% of equity: ${max_position_value:.2f}")
        elif position_value < min_position_value:
            adjusted_position_size = min_position_value / entry_price
            logger.info(f"Position size increased to minimum: ${min_position_value:.2f}")
        
        logger.info(f"Position size: {adjusted_position_size:.4f} (${adjusted_position_size * entry_price:.2f})")
        return adjusted_position_size

    def record_trade_result(self, trade_result: dict):
        """Record trade result and update risk parameters"""
        
        # Add to recent trades
        self.recent_trades.append(trade_result)
        if len(self.recent_trades) > self.max_recent_trades:
            self.recent_trades.pop(0)
        
        # Update consecutive loss count
        pnl = trade_result.get('pnl', 0)
        if pnl < 0:
            self.consecutive_loss_count += 1
            self.last_loss_time = datetime.now()
            
            # NEW: Update loss pattern analysis
            self.loss_patterns['stop_loss_hits'] += 1
            
            loss_pct = abs(trade_result.get('pnl_pct', 0))
            if loss_pct > 0.02:  # >2% loss
                self.loss_patterns['large_losses'] += 1
            
            duration = trade_result.get('duration_hours', 0)
            if duration < 1:  # <1 hour
                self.loss_patterns['quick_losses'] += 1
            
            logger.warning(f"Trade loss recorded. Consecutive losses: {self.consecutive_loss_count}/{self.max_consecutive_losses}")
            
            # NEW: Implement emergency stop if too many large losses
            if self.loss_patterns['large_losses'] >= 3:
                logger.error("Too many large losses detected - implementing emergency stop")
                self.consecutive_loss_count = self.max_consecutive_losses
        else:
            # Reset consecutive loss count on win
            self.consecutive_loss_count = 0
            logger.info("Trade win recorded - resetting consecutive loss count")
        
        # Update risk parameters
        self._adjust_risk_parameters()
        
        # NEW: Log risk status
        logger.info(f"Risk status: consecutive_losses={self.consecutive_loss_count}, risk_pct={self.risk_per_trade_pct*100:.2f}%, risk_multiplier={self.risk_multiplier:.2f}")

    def get_risk_summary(self) -> dict:
        """Get comprehensive risk summary"""
        return {
            'current_equity': self.current_equity,
            'risk_per_trade_pct': self.risk_per_trade_pct,
            'consecutive_losses': self.consecutive_loss_count,
            'max_consecutive_losses': self.max_consecutive_losses,
            'risk_multiplier': self.risk_multiplier,
            'recent_trades_count': len(self.recent_trades),
            'win_rate': self._calculate_win_rate(),
            'loss_patterns': self.loss_patterns.copy(),
            'can_trade': self.can_trade()[0]
        }

    def _calculate_win_rate(self) -> float:
        """Calculate current win rate"""
        if not self.recent_trades:
            return 0.0
        wins = sum(1 for trade in self.recent_trades if trade.get('pnl', 0) > 0)
        return wins / len(self.recent_trades)

    def _calculate_daily_pnl(self) -> float:
        """Calculate today's P&L"""
        today = datetime.now().date()
        daily_pnl = 0.0
        
        for trade in self.recent_trades:
            trade_date = trade.get('exit_time', datetime.now()).date()
            if trade_date == today:
                daily_pnl += trade.get('pnl', 0)
        
        return daily_pnl


# Legacy functions for backward compatibility
def calculate_risk_reward_ratio(entry_price: float, stop_price: float, 
                               target_price: float) -> float:
    """Calculate risk-reward ratio"""
    try:
        risk = abs(entry_price - stop_price)
        reward = abs(target_price - entry_price)
        
        if risk == 0:
            return 0.0
        
        return reward / risk
        
    except Exception as e:
        logger.error(f"Error calculating risk-reward ratio: {e}")
        return 0.0


def validate_position_size(qty: float, min_qty: float, max_qty: float) -> bool:
    """Validate position size within limits"""
    try:
        return min_qty <= qty <= max_qty
    except Exception as e:
        logger.error(f"Error validating position size: {e}")
        return False


def calculate_max_position_size(equity: float, max_risk_pct: float, 
                              entry_price: float) -> float:
    """Calculate maximum position size based on equity and max risk"""
    try:
        max_risk_amount = equity * max_risk_pct
        max_qty = max_risk_amount / entry_price
        return max_qty
    except Exception as e:
        logger.error(f"Error calculating max position size: {e}")
        return 0.0
