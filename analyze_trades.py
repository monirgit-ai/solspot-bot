#!/usr/bin/env python3

import requests
import pandas as pd
import numpy as np
import ta
from datetime import datetime
import sqlite3

def get_market_data():
    """Get recent SOLUSDT market data"""
    url = 'https://api.binance.com/api/v3/klines?symbol=SOLUSDT&interval=15m&limit=100'
    response = requests.get(url)
    data = response.json()
    
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                   'close_time', 'quote_volume', 'trades', 'taker_buy_base', 
                                   'taker_buy_quote', 'ignore'])
    df = df.astype(float)
    return df

def calculate_indicators(df):
    """Calculate technical indicators"""
    df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
    df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['ema_diff'] = df['ema20'] - df['ema50']
    df['ema_diff_pct'] = abs(df['ema_diff']) / df['close']
    return df

def analyze_trade_entry(df, entry_time_str):
    """Analyze market conditions at trade entry"""
    entry_dt = datetime.strptime(entry_time_str, '%Y-%m-%d %H:%M:%S')
    entry_timestamp = int(entry_dt.timestamp() * 1000)
    
    # Find the candle containing the entry time
    entry_candle_idx = None
    for i, timestamp in enumerate(df['timestamp']):
        if timestamp <= entry_timestamp < timestamp + 900000:  # 15 minutes
            entry_candle_idx = i
            break
    
    if entry_candle_idx is None:
        return None
    
    # Get data up to entry candle
    entry_df = df.iloc[:entry_candle_idx+1]
    entry_df = calculate_indicators(entry_df)
    
    latest = entry_df.iloc[-1]
    
    # Check entry conditions
    condition1 = latest['close'] > latest['ema20']
    condition2 = latest['ema20'] > latest['ema50']
    condition3 = latest['rsi'] > 50
    in_chop = (latest['ema_diff_pct'] < 0.003) and (45 <= latest['rsi'] <= 55)
    
    return {
        'entry_price': latest['close'],
        'ema20': latest['ema20'],
        'ema50': latest['ema50'],
        'rsi': latest['rsi'],
        'atr': latest['atr'],
        'ema_diff_pct': latest['ema_diff_pct'],
        'condition1': condition1,
        'condition2': condition2,
        'condition3': condition3,
        'in_chop': in_chop,
        'long_signal': condition1 and condition2 and condition3 and not in_chop
    }

def get_trades_from_db():
    """Get last 3 trades from database"""
    conn = sqlite3.connect('solspot_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, entry_ts, exit_ts, symbol, qty, entry_price, exit_price, 
               sl, tp1, pnl_usdt, pnl_pct, reason_exit 
        FROM trades 
        ORDER BY entry_ts DESC 
        LIMIT 3
    """)
    
    trades = cursor.fetchall()
    conn.close()
    
    return trades

def main():
    print("=== SOLUSDT Trading Bot Analysis ===\n")
    
    # Get market data
    print("Fetching market data...")
    df = get_market_data()
    df = calculate_indicators(df)
    
    # Current market analysis
    latest = df.iloc[-1]
    print(f"\n=== Current Market Conditions ===")
    print(f"Current Price: ${latest['close']:.2f}")
    print(f"EMA20: ${latest['ema20']:.2f}")
    print(f"EMA50: ${latest['ema50']:.2f}")
    print(f"RSI: {latest['rsi']:.1f}")
    print(f"ATR: ${latest['atr']:.2f}")
    print(f"EMA Diff %: {latest['ema_diff_pct']*100:.2f}%")
    
    # Current entry conditions
    condition1 = latest['close'] > latest['ema20']
    condition2 = latest['ema20'] > latest['ema50']
    condition3 = latest['rsi'] > 50
    in_chop = (latest['ema_diff_pct'] < 0.003) and (45 <= latest['rsi'] <= 55)
    
    print(f"\n=== Current Entry Conditions ===")
    print(f"Close > EMA20: {condition1} ({latest['close']:.2f} > {latest['ema20']:.2f})")
    print(f"EMA20 > EMA50: {condition2} ({latest['ema20']:.2f} > {latest['ema50']:.2f})")
    print(f"RSI > 50: {condition3} ({latest['rsi']:.1f} > 50)")
    print(f"In Chop: {in_chop} (EMA diff: {latest['ema_diff_pct']*100:.2f}%, RSI: {latest['rsi']:.1f})")
    
    # Get trades from database
    trades = get_trades_from_db()
    
    print(f"\n=== Last 3 Trades Analysis ===")
    
    for i, trade in enumerate(trades):
        trade_id, entry_ts, exit_ts, symbol, qty, entry_price, exit_price, sl, tp1, pnl_usdt, pnl_pct, reason_exit = trade
        
        print(f"\n--- Trade #{trade_id} ---")
        print(f"Entry Time: {entry_ts}")
        print(f"Entry Price: ${entry_price:.2f}")
        print(f"Quantity: {qty} SOL")
        print(f"Stop Loss: ${sl:.2f}")
        print(f"Take Profit: ${tp1:.2f}")
        
        if exit_price:
            print(f"Exit Price: ${exit_price:.2f}")
            print(f"P&L: ${pnl_usdt:.2f} ({pnl_pct*100:.2f}%)")
            print(f"Exit Reason: {reason_exit}")
        else:
            print("Status: OPEN")
        
        # Analyze entry conditions
        entry_analysis = analyze_trade_entry(df, entry_ts)
        if entry_analysis:
            print(f"\nEntry Analysis:")
            print(f"  Close: ${entry_analysis['entry_price']:.2f}")
            print(f"  EMA20: ${entry_analysis['ema20']:.2f}")
            print(f"  EMA50: ${entry_analysis['ema50']:.2f}")
            print(f"  RSI: {entry_analysis['rsi']:.1f}")
            print(f"  ATR: ${entry_analysis['atr']:.2f}")
            print(f"  EMA Diff %: {entry_analysis['ema_diff_pct']*100:.2f}%")
            print(f"  Long Signal: {entry_analysis['long_signal']}")
            
            if not entry_analysis['long_signal']:
                reasons = []
                if not entry_analysis['condition1']:
                    reasons.append("Close <= EMA20")
                if not entry_analysis['condition2']:
                    reasons.append("EMA20 <= EMA50")
                if not entry_analysis['condition3']:
                    reasons.append("RSI <= 50")
                if entry_analysis['in_chop']:
                    reasons.append("In choppy market")
                print(f"  Signal Rejected: {', '.join(reasons)}")
    
    # Market trend analysis
    print(f"\n=== Market Trend Analysis ===")
    recent_prices = df['close'].tail(20).values
    price_change = ((recent_prices[-1] - recent_prices[0]) / recent_prices[0]) * 100
    print(f"Last 20 candles price change: {price_change:.2f}%")
    
    recent_atr = df['atr'].tail(10).mean()
    atr_pct = (recent_atr / latest['close']) * 100
    print(f"Average ATR (last 10): ${recent_atr:.2f} ({atr_pct:.2f}% of price)")
    
    # Volatility analysis
    volatility = df['atr'].tail(20).std()
    print(f"ATR Volatility: ${volatility:.2f}")
    
    # Trend strength
    ema_diff_trend = df['ema_diff_pct'].tail(10).mean()
    print(f"Average EMA Diff %: {ema_diff_trend*100:.2f}%")

if __name__ == "__main__":
    main()
