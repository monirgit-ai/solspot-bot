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
    """Comprehensive risk management system"""
    
    def __init__(self, initial_equity: float, risk_per_trade_pct: float = 0.005, 
                 daily_loss_stop_pct: float = 0.015, cooldown_bars: int = 1):
        """
        Initialize risk manager
        
        Args:
            initial_equity: Starting equity in USDT
            risk_per_trade_pct: Risk per trade as percentage (0.005 = 0.5%)
            daily_loss_stop_pct: Daily loss stop as percentage (0.015 = 1.5%)
            cooldown_bars: Number of bars to wait after trade close
        """
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.risk_per_trade_pct = risk_per_trade_pct
        self.daily_loss_stop_pct = daily_loss_stop_pct
        self.cooldown_tracker = CooldownTracker(cooldown_bars)
        
        # Daily tracking
        self.today_start_equity = initial_equity
        self.today_pnl = 0.0
        self.trades_today = 0
        self.last_trade_date = None
        
        logger.info(f"Risk manager initialized: equity=${initial_equity:.2f}, risk={risk_per_trade_pct*100:.1f}%, daily_stop={daily_loss_stop_pct*100:.1f}%")
    
    def update_equity(self, new_equity: float) -> None:
        """Update current equity and recalculate daily P&L"""
        self.current_equity = new_equity
        # Recalculate daily P&L based on current equity vs start equity
        self.today_pnl = new_equity - self.today_start_equity
        logger.info(f"Equity updated: ${new_equity:.2f}, Daily P&L: ${self.today_pnl:.2f}")
    
    def update_daily_pnl(self, pnl: float) -> None:
        """Update today's P&L"""
        self.today_pnl = pnl
    
    def increment_trades_today(self) -> None:
        """Increment today's trade count"""
        self.trades_today += 1
    
    def reset_daily_tracking(self) -> None:
        """Reset daily tracking (call at start of new day)"""
        today = date.today()
        if self.last_trade_date != today:
            self.today_start_equity = self.current_equity
            self.today_pnl = 0.0
            self.trades_today = 0
            self.last_trade_date = today
            logger.info("Daily tracking reset")
    
    def calculate_position_size(self, entry_price: float, stop_price: float, 
                              lot_step: float) -> float:
        """
        Calculate position size using current equity
        
        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            lot_step: Minimum lot size step
        
        Returns:
            float: Position quantity
        """
        return position_size(
            self.current_equity,
            entry_price,
            stop_price,
            self.risk_per_trade_pct,
            lot_step
        )
    
    def check_daily_guardrails(self) -> bool:
        """
        Check if trading should continue based on daily limits
        
        Returns:
            bool: True if trading should continue
        """
        return daily_guardrails(
            self.trades_today,
            self.today_pnl,
            self.daily_loss_stop_pct,
            self.today_start_equity
        )
    
    def can_open_trade(self, current_bar: int) -> bool:
        """
        Check if a new trade can be opened
        
        Args:
            current_bar: Current bar number/timestamp
        
        Returns:
            bool: True if trade can be opened
        """
        # Update cooldown tracker
        self.cooldown_tracker.update_bar(current_bar)
        
        # Log cooldown status
        cooldown_status = self.cooldown_tracker.get_cooldown_status()
        logger.info(f"Cooldown status: {cooldown_status}")
        
        # Check daily guardrails
        if not self.check_daily_guardrails():
            logger.warning("Daily guardrails prevent new trade")
            return False
        
        # Check cooldown
        if not self.cooldown_tracker.can_trade():
            logger.info("Cooldown period active, cannot trade")
            return False
        
        return True
    
    def record_trade_close(self, current_bar: int) -> None:
        """Record when a trade is closed"""
        self.cooldown_tracker.record_trade_close(current_bar)
    
    def get_risk_summary(self) -> Dict:
        """
        Get comprehensive risk summary
        
        Returns:
            dict: Risk summary information
        """
        return {
            'current_equity': self.current_equity,
            'today_start_equity': self.today_start_equity,
            'today_pnl': self.today_pnl,
            'trades_today': self.trades_today,
            'risk_per_trade_pct': self.risk_per_trade_pct,
            'daily_loss_stop_pct': self.daily_loss_stop_pct,
            'cooldown_status': self.cooldown_tracker.get_cooldown_status(),
            'can_trade': self.cooldown_tracker.can_trade()
        }


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
