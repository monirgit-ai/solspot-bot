import pandas as pd
import numpy as np
import ta
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA)
    
    Args:
        data: Price series (usually close prices)
        period: EMA period
    
    Returns:
        pd.Series: EMA values
    """
    try:
        return ta.trend.ema_indicator(data, window=period)
    except Exception as e:
        logger.error(f"Error calculating EMA({period}): {e}")
        return pd.Series([np.nan] * len(data), index=data.index)


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI)
    
    Args:
        data: Price series (usually close prices)
        period: RSI period (default 14)
    
    Returns:
        pd.Series: RSI values (0-100)
    """
    try:
        return ta.momentum.rsi(data, window=period)
    except Exception as e:
        logger.error(f"Error calculating RSI({period}): {e}")
        return pd.Series([np.nan] * len(data), index=data.index)


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ATR period (default 14)
    
    Returns:
        pd.Series: ATR values
    """
    try:
        return ta.volatility.average_true_range(high, low, close, window=period)
    except Exception as e:
        logger.error(f"Error calculating ATR({period}): {e}")
        return pd.Series([np.nan] * len(close), index=close.index)


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators for a DataFrame
    
    Args:
        df: DataFrame with OHLCV data (must have 'high', 'low', 'close' columns)
    
    Returns:
        pd.DataFrame: Original data with added indicator columns
    """
    try:
        # Make a copy to avoid modifying original
        result_df = df.copy()
        
        # Calculate EMAs
        result_df['ema20'] = calculate_ema(result_df['close'], 20)
        result_df['ema50'] = calculate_ema(result_df['close'], 50)
        
        # Calculate RSI
        result_df['rsi'] = calculate_rsi(result_df['close'], 14)
        
        # Calculate ATR
        result_df['atr'] = calculate_atr(result_df['high'], result_df['low'], result_df['close'], 14)
        
        # Calculate additional derived indicators
        result_df['ema_diff'] = result_df['ema20'] - result_df['ema50']
        result_df['ema_diff_pct'] = abs(result_df['ema_diff']) / result_df['close']
        
        logger.info(f"Calculated indicators for {len(result_df)} data points")
        return result_df
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        return df


def is_valid_data(df: pd.DataFrame) -> bool:
    """
    Check if DataFrame has valid data for indicator calculation
    
    Args:
        df: DataFrame to validate
    
    Returns:
        bool: True if data is valid
    """
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    
    # Check if all required columns exist
    if not all(col in df.columns for col in required_columns):
        logger.error(f"Missing required columns. Need: {required_columns}")
        return False
    
    # Check if DataFrame is not empty
    if len(df) == 0:
        logger.error("DataFrame is empty")
        return False
    
    # Check if we have enough data for calculations (need at least 50 periods for EMA50)
    if len(df) < 50:
        logger.error(f"Not enough data points. Need at least 50, got {len(df)}")
        return False
    
    # Check for NaN values in required columns
    for col in required_columns:
        if df[col].isna().all():
            logger.error(f"All values in {col} are NaN")
            return False
    
    return True


def get_latest_indicators(df: pd.DataFrame) -> dict:
    """
    Get the latest indicator values from a DataFrame
    
    Args:
        df: DataFrame with calculated indicators
    
    Returns:
        dict: Latest indicator values
    """
    try:
        if not is_valid_data(df):
            return {}
        
        # Calculate indicators if not already present
        if 'ema20' not in df.columns:
            df = calculate_all_indicators(df)
        
        # Get the latest values
        latest = df.iloc[-1]
        
        return {
            'close': latest['close'],
            'ema20': latest['ema20'],
            'ema50': latest['ema50'],
            'rsi': latest['rsi'],
            'atr': latest['atr'],
            'ema_diff_pct': latest['ema_diff_pct']
        }
        
    except Exception as e:
        logger.error(f"Error getting latest indicators: {e}")
        return {}


# Legacy functions for backward compatibility
def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average (SMA)"""
    try:
        return ta.trend.sma_indicator(data, window=period)
    except Exception as e:
        logger.error(f"Error calculating SMA({period}): {e}")
        return pd.Series([np.nan] * len(data), index=data.index)


def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands"""
    try:
        bb = ta.volatility.BollingerBands(data, window=period, window_dev=std_dev)
        return bb.bollinger_hband(), bb.bollinger_lband(), bb.bollinger_mavg()
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {e}")
        nan_series = pd.Series([np.nan] * len(data), index=data.index)
        return nan_series, nan_series, nan_series


def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD"""
    try:
        macd = ta.trend.MACD(data, window_fast=fast, window_slow=slow, window_sign=signal)
        return macd.macd(), macd.macd_signal(), macd.macd_diff()
    except Exception as e:
        logger.error(f"Error calculating MACD: {e}")
        nan_series = pd.Series([np.nan] * len(data), index=data.index)
        return nan_series, nan_series, nan_series
