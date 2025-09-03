import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional
from .indicators import calculate_all_indicators, is_valid_data, get_latest_indicators

logger = logging.getLogger(__name__)


def generate_signal(df: pd.DataFrame) -> Dict:
    """
    Generate trading signal based on technical indicators
    
    Entry long when:
    - close > ema20, ema20 > ema50, rsi > 50
    - Not in chop: |ema20-ema50|/close >= 0.003 or rsi not in [45,55]
    - sl = close - 1.8*atr, tp1 = close + 1.5*atr
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        dict: Signal information with keys:
            - signal: 'long' | 'flat'
            - sl: stop loss price
            - tp1: take profit 1 price
            - entry_ref_price: reference price for entry
    """
    try:
        # Validate input data
        if not is_valid_data(df):
            logger.warning("Invalid data for signal generation")
            return {
                'signal': 'flat',
                'sl': None,
                'tp1': None,
                'entry_ref_price': None
            }
        
        # Calculate indicators
        df_with_indicators = calculate_all_indicators(df)
        
        # Get latest values
        latest = df_with_indicators.iloc[-1]
        
        close = latest['close']
        ema20 = latest['ema20']
        ema50 = latest['ema50']
        rsi = latest['rsi']
        atr = latest['atr']
        ema_diff_pct = latest['ema_diff_pct']
        
        # Check for NaN values
        if pd.isna(close) or pd.isna(ema20) or pd.isna(ema50) or pd.isna(rsi) or pd.isna(atr):
            logger.warning("NaN values in indicators, cannot generate signal")
            return {
                'signal': 'flat',
                'sl': None,
                'tp1': None,
                'entry_ref_price': None
            }
        
        # ENHANCED: Entry conditions for long position with better timing
        condition1 = close > ema20  # Close above EMA20
        condition2 = ema20 > ema50  # EMA20 above EMA50 (uptrend)
        condition3 = rsi > 50  # RSI above 50 (momentum)
        
        # NEW: Enhanced trend strength requirement (from loss analysis)
        condition4 = ema_diff_pct >= 0.005  # Stronger trend (0.5% vs 0.3%)
        
        # NEW: Avoid overbought conditions (from loss analysis)
        condition5 = rsi < 70  # RSI not overbought
        
        # NEW: Avoid oversold conditions
        condition6 = rsi > 30  # RSI not oversold
        
        # NEW: Minimum volatility requirement
        condition7 = atr >= close * 0.003  # ATR at least 0.3% of price
        
        # ENHANCED: Better chop detection
        in_chop = (ema_diff_pct < 0.003) and (45 <= rsi <= 55)
        not_in_chop = not in_chop
        
        # NEW: Time-based filter (avoid worst trading hours from loss analysis)
        current_hour = pd.Timestamp.now().hour
        avoid_hours = list(range(6, 12))  # 06:00-12:00 (worst performing)
        good_timing = current_hour not in avoid_hours
        
        # NEW: Day-based filter (avoid Sunday trading from loss analysis)
        current_day = pd.Timestamp.now().strftime('%A')
        avoid_days = ['Sunday']  # Worst performing day
        good_day = current_day not in avoid_days
        
        # All conditions must be met for long signal
        long_signal = (condition1 and condition2 and condition3 and condition4 and 
                      condition5 and condition6 and condition7 and not_in_chop and 
                      good_timing and good_day)
        
        if long_signal:
            # Calculate stop loss and take profit with new multiplier
            sl = close - 2.2 * atr  # Increased from 1.8 to 2.2
            tp1 = close + 1.5 * atr
            
            # Ensure stop loss is positive
            if sl <= 0:
                logger.warning("Stop loss would be negative, using 5% below close")
                sl = close * 0.95
            
            logger.info(f"LONG signal generated - Close: {close:.2f}, SL: {sl:.2f}, TP1: {tp1:.2f}")
            logger.info(f"Signal quality: Trend strength {ema_diff_pct*100:.2f}%, RSI: {rsi:.1f}, ATR: {atr:.2f}")
            
            return {
                'signal': 'long',
                'sl': sl,
                'tp1': tp1,
                'entry_ref_price': close,
                'indicators': {
                    'close': close,
                    'ema20': ema20,
                    'ema50': ema50,
                    'rsi': rsi,
                    'atr': atr,
                    'ema_diff_pct': ema_diff_pct,
                    'signal_strength': min(ema_diff_pct * 1000, 100)  # 0-100 scale
                }
            }
        else:
            # Log why signal was not generated with enhanced details
            reasons = []
            if not condition1:
                reasons.append(f"close({close:.2f}) <= ema20({ema20:.2f})")
            if not condition2:
                reasons.append(f"ema20({ema20:.2f}) <= ema50({ema50:.2f})")
            if not condition3:
                reasons.append(f"rsi({rsi:.1f}) <= 50")
            if not condition4:
                reasons.append(f"weak_trend(ema_diff_pct={ema_diff_pct:.4f} < 0.005)")
            if not condition5:
                reasons.append(f"overbought(rsi={rsi:.1f} >= 70)")
            if not condition6:
                reasons.append(f"oversold(rsi={rsi:.1f} <= 30)")
            if not condition7:
                reasons.append(f"low_volatility(atr={atr:.2f}, {atr/close*100:.2f}% of price)")
            if in_chop:
                reasons.append(f"in_chop(ema_diff_pct={ema_diff_pct:.4f}, rsi={rsi:.1f})")
            if not good_timing:
                reasons.append(f"bad_timing(hour {current_hour} in avoid_hours {avoid_hours})")
            if not good_day:
                reasons.append(f"bad_day({current_day} in avoid_days {avoid_days})")
            
            logger.debug(f"No long signal - reasons: {', '.join(reasons)}")
            
            return {
                'signal': 'flat',
                'sl': None,
                'tp1': None,
                'entry_ref_price': None,
                'indicators': {
                    'close': close,
                    'ema20': ema20,
                    'ema50': ema50,
                    'rsi': rsi,
                    'atr': atr,
                    'ema_diff_pct': ema_diff_pct,
                    'rejected_reasons': reasons
                }
            }
            
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return {
            'signal': 'flat',
            'sl': None,
            'tp1': None,
            'entry_ref_price': None
        }


def analyze_market_conditions(df: pd.DataFrame) -> Dict:
    """
    Analyze current market conditions
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        dict: Market analysis
    """
    try:
        if not is_valid_data(df):
            return {}
        
        indicators = get_latest_indicators(df)
        if not indicators:
            return {}
        
        close = indicators['close']
        ema20 = indicators['ema20']
        ema50 = indicators['ema50']
        rsi = indicators['rsi']
        atr = indicators['atr']
        ema_diff_pct = indicators['ema_diff_pct']
        
        # Determine trend
        if ema20 > ema50:
            trend = "uptrend"
        elif ema20 < ema50:
            trend = "downtrend"
        else:
            trend = "sideways"
        
        # Determine momentum
        if rsi > 70:
            momentum = "overbought"
        elif rsi < 30:
            momentum = "oversold"
        elif rsi > 50:
            momentum = "bullish"
        else:
            momentum = "bearish"
        
        # Determine volatility
        if atr > close * 0.05:  # ATR > 5% of close
            volatility = "high"
        elif atr < close * 0.02:  # ATR < 2% of close
            volatility = "low"
        else:
            volatility = "medium"
        
        # Determine if in chop
        in_chop = (ema_diff_pct < 0.003) and (45 <= rsi <= 55)
        
        return {
            'trend': trend,
            'momentum': momentum,
            'volatility': volatility,
            'in_chop': in_chop,
            'indicators': indicators
        }
        
    except Exception as e:
        logger.error(f"Error analyzing market conditions: {e}")
        return {}


def validate_signal_quality(signal: Dict) -> bool:
    """
    Validate the quality of a generated signal
    
    Args:
        signal: Signal dictionary from generate_signal()
    
    Returns:
        bool: True if signal quality is acceptable
    """
    try:
        if signal['signal'] != 'long':
            return False
        
        close = signal['entry_ref_price']
        sl = signal['sl']
        tp1 = signal['tp1']
        
        # Check if stop loss and take profit are reasonable
        if sl is None or tp1 is None or close is None:
            return False
        
        # Stop loss should be below entry price
        if sl >= close:
            logger.warning("Stop loss is not below entry price")
            return False
        
        # Take profit should be above entry price
        if tp1 <= close:
            logger.warning("Take profit is not above entry price")
            return False
        
        # Risk-reward ratio should be reasonable (at least 1:1)
        risk = close - sl
        reward = tp1 - close
        rr_ratio = reward / risk if risk > 0 else 0
        
        if rr_ratio < 0.8:  # Allow some flexibility
            logger.warning(f"Risk-reward ratio too low: {rr_ratio:.2f}")
            return False
        
        # Stop loss should not be too close (at least 1% away)
        sl_distance_pct = (close - sl) / close
        if sl_distance_pct < 0.01:
            logger.warning(f"Stop loss too close: {sl_distance_pct:.3f}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating signal quality: {e}")
        return False


# Legacy functions for backward compatibility
def generate_basic_signal(df: pd.DataFrame) -> str:
    """Legacy basic signal generation"""
    try:
        signal = generate_signal(df)
        return signal['signal']
    except Exception as e:
        logger.error(f"Error in basic signal generation: {e}")
        return 'flat'


def get_signal_strength(df: pd.DataFrame) -> float:
    """
    Get signal strength (0-1) based on how many conditions are met
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        float: Signal strength (0-1)
    """
    try:
        if not is_valid_data(df):
            return 0.0
        
        indicators = get_latest_indicators(df)
        if not indicators:
            return 0.0
        
        close = indicators['close']
        ema20 = indicators['ema20']
        ema50 = indicators['ema50']
        rsi = indicators['rsi']
        ema_diff_pct = indicators['ema_diff_pct']
        
        # Count conditions met
        conditions_met = 0
        total_conditions = 4
        
        if close > ema20:
            conditions_met += 1
        if ema20 > ema50:
            conditions_met += 1
        if rsi > 50:
            conditions_met += 1
        if not ((ema_diff_pct < 0.003) and (45 <= rsi <= 55)):
            conditions_met += 1
        
        return conditions_met / total_conditions
        
    except Exception as e:
        logger.error(f"Error calculating signal strength: {e}")
        return 0.0
