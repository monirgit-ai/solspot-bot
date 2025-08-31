from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import get_db
from ..repo import TradeRepository, OrderRepository, EquityRepository, AlertRepository
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

router = APIRouter()
templates = Jinja2Templates(directory="api/app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Trading dashboard page"""
    from ..config import settings
    import httpx
    import time
    import hmac
    import hashlib
    
    trade_repo = TradeRepository(db)
    order_repo = OrderRepository(db)
    equity_repo = EquityRepository(db)
    alert_repo = AlertRepository(db)
    
    # Get recent data from database
    recent_trades = trade_repo.recent_trades(limit=5)
    open_trades = trade_repo.get_open_trades()
    recent_orders = order_repo.recent_orders(limit=5)
    recent_alerts = alert_repo.get_recent_alerts(limit=5)
    trade_summary = trade_repo.get_trade_summary()
    
    # Get live account data if in live mode
    live_equity = 0.0
    live_balances = []
    
    if settings.MODE == "live":
        try:
            # Get real account balance from Binance
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(
                settings.BINANCE_API_SECRET.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            url = "https://api.binance.com/api/v3/account"
            params = {
                'timestamp': timestamp,
                'signature': signature
            }
            headers = {
                'X-MBX-APIKEY': settings.BINANCE_API_KEY
            }
            
            with httpx.Client() as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                account_data = response.json()
                
                # Calculate live equity
                for balance in account_data.get('balances', []):
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    
                    if total > 0:
                        live_balances.append({
                            'asset': asset,
                            'free': free,
                            'locked': locked,
                            'total': total
                        })
                        
                        # Get current price for non-USDT assets to calculate equity
                        if asset != 'USDT':
                            try:
                                price_response = client.get(
                                    "https://api.binance.com/api/v3/ticker/price",
                                    params={'symbol': f"{asset}USDT"}
                                )
                                if price_response.status_code == 200:
                                    price_data = price_response.json()
                                    asset_price = float(price_data['price'])
                                    live_equity += total * asset_price
                                else:
                                    # If no USDT pair, assume 1:1 for stablecoins
                                    live_equity += total
                            except:
                                # If price fetch fails, assume 1:1 for stablecoins
                                live_equity += total
                        else:
                            live_equity += total
                
        except Exception as e:
            # Fallback to database data if live fetch fails
            latest_equity = equity_repo.latest_equity()
            live_equity = latest_equity.equity_usdt if latest_equity else 1000.0
            today_metrics = equity_repo.today_metrics()
    else:
        # Paper mode - use database data
        latest_equity = equity_repo.latest_equity()
        live_equity = latest_equity.equity_usdt if latest_equity else 1000.0
        today_metrics = equity_repo.today_metrics()
    
    # Get initial equity from config for accurate P&L calculation
    try:
        import sys
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, project_root)
        from trading_config import INITIAL_EQUITY
        initial_equity = INITIAL_EQUITY
    except ImportError:
        initial_equity = 1000.0  # Fallback
    
    # Calculate today's P&L using actual initial equity
    today_pnl = live_equity - initial_equity
    
    # Get current SOL price for title
    current_sol_price = None
    try:
        with httpx.Client() as client:
            price_response = client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={'symbol': 'SOLUSDT'}
            )
            if price_response.status_code == 200:
                price_data = price_response.json()
                current_sol_price = float(price_data['price'])
    except Exception as e:
        # If price fetch fails, use None
        current_sol_price = None
    
    context = {
        "request": request,
        "trades": recent_trades,
        "open_trades": open_trades,
        "orders": recent_orders,
        "latest_equity": {"equity_usdt": live_equity},
        "today_metrics": {
            "start_equity": initial_equity,
            "current_equity": live_equity,
            "daily_pnl": today_pnl,
            "daily_pnl_pct": (today_pnl / initial_equity * 100) if initial_equity > 0 else 0,
            "snapshots_count": 1
        },
        "alerts": recent_alerts,
        "trade_summary": trade_summary,
        "total_trades": trade_summary['total_trades'],
        "open_trades_count": len(open_trades),
        "live_balances": live_balances,
        "mode": settings.MODE,
        "current_sol_price": current_sol_price
    }
    
    return templates.TemplateResponse("dashboard.html", context)


@router.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    """Configuration page"""
    # Load current configuration
    try:
        import sys
        import os
        # Add the project root to the path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, project_root)
        
        # Import configuration with error handling
        try:
            from trading_config import (
                TRADING_SYMBOL, TIMEFRAME, INITIAL_EQUITY, RISK_PER_TRADE_PCT,
                DAILY_LOSS_STOP_PCT, COOLDOWN_BARS, STOP_LOSS_PCT, TAKE_PROFIT_1_PCT,
                TAKE_PROFIT_2_PCT, MAX_POSITION_SIZE_PCT, MIN_POSITION_SIZE_USDT,
                RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
                TELEGRAM_ENABLED, HEARTBEAT_INTERVAL_HOURS, DAILY_REPORT_TIME,
                MAX_DRAWDOWN_PCT, MAX_API_FAILURES
            )
        except ImportError as e:
            # If import fails, use default values
            raise ImportError(f"Could not import trading_config: {e}")
        
        config = {
            "trading_symbol": TRADING_SYMBOL,
            "timeframe": TIMEFRAME,
            "initial_equity": INITIAL_EQUITY,
            "risk_per_trade_pct": RISK_PER_TRADE_PCT * 100,  # Convert to percentage
            "daily_loss_stop_pct": DAILY_LOSS_STOP_PCT * 100,
            "cooldown_bars": COOLDOWN_BARS,
            "stop_loss_pct": STOP_LOSS_PCT * 100,
            "take_profit_1_pct": TAKE_PROFIT_1_PCT * 100,
            "take_profit_2_pct": TAKE_PROFIT_2_PCT * 100,
            "max_position_size_pct": MAX_POSITION_SIZE_PCT * 100,
            "min_position_size_usdt": MIN_POSITION_SIZE_USDT,
            "rsi_period": RSI_PERIOD,
            "rsi_overbought": RSI_OVERBOUGHT,
            "rsi_oversold": RSI_OVERSOLD,
            "macd_fast": MACD_FAST,
            "macd_slow": MACD_SLOW,
            "macd_signal": MACD_SIGNAL,
            "telegram_enabled": TELEGRAM_ENABLED,
            "heartbeat_interval_hours": HEARTBEAT_INTERVAL_HOURS,
            "daily_report_time": DAILY_REPORT_TIME,
            "max_drawdown_pct": MAX_DRAWDOWN_PCT,
            "max_api_failures": MAX_API_FAILURES
        }
    except ImportError:
        # Default configuration if file doesn't exist
        config = {
            "trading_symbol": "SOLUSDT",
            "timeframe": "15m",
            "initial_equity": 10000.0,
            "risk_per_trade_pct": 0.5,
            "daily_loss_stop_pct": 1.5,
            "cooldown_bars": 1,
            "stop_loss_pct": 2.0,
            "take_profit_1_pct": 4.0,
            "take_profit_2_pct": 8.0,
            "max_position_size_pct": 10.0,
            "min_position_size_usdt": 10.0,
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9,
            "telegram_enabled": True,
            "heartbeat_interval_hours": 6,
            "daily_report_time": "23:59",
            "max_drawdown_pct": 12.0,
            "max_api_failures": 5
        }
    
    context = {
        "request": request,
        "config": config
    }
    
    return templates.TemplateResponse("config.html", context)


@router.post("/config/save")
async def save_config(request: Request):
    """Save configuration changes"""
    try:
        import os
        form_data = await request.form()
        
        # Generate new configuration content
        config_content = f"""# Trading Configuration
# Auto-generated by web UI

# Trading Symbol and Timeframe
TRADING_SYMBOL = "{form_data.get('trading_symbol', 'SOLUSDT')}"
TIMEFRAME = "{form_data.get('timeframe', '15m')}"

# Risk Management
INITIAL_EQUITY = {float(form_data.get('initial_equity', 10000.0))}
RISK_PER_TRADE_PCT = {float(form_data.get('risk_per_trade_pct', 0.5)) / 100}
DAILY_LOSS_STOP_PCT = {float(form_data.get('daily_loss_stop_pct', 1.5)) / 100}
COOLDOWN_BARS = {int(form_data.get('cooldown_bars', 1))}

# Position Sizing
MAX_POSITION_SIZE_PCT = {float(form_data.get('max_position_size_pct', 10.0)) / 100}
MIN_POSITION_SIZE_USDT = {float(form_data.get('min_position_size_usdt', 10.0))}

# Stop Loss and Take Profit
STOP_LOSS_PCT = {float(form_data.get('stop_loss_pct', 2.0)) / 100}
TAKE_PROFIT_1_PCT = {float(form_data.get('take_profit_1_pct', 4.0)) / 100}
TAKE_PROFIT_2_PCT = {float(form_data.get('take_profit_2_pct', 8.0)) / 100}

# Trading Schedule
TRADING_HOURS_START = 0
TRADING_HOURS_END = 24

# Technical Analysis
RSI_PERIOD = {int(form_data.get('rsi_period', 14))}
RSI_OVERBOUGHT = {int(form_data.get('rsi_overbought', 70))}
RSI_OVERSOLD = {int(form_data.get('rsi_oversold', 30))}
MACD_FAST = {int(form_data.get('macd_fast', 12))}
MACD_SLOW = {int(form_data.get('macd_slow', 26))}
MACD_SIGNAL = {int(form_data.get('macd_signal', 9))}

# Notifications
TELEGRAM_ENABLED = True
HEARTBEAT_INTERVAL_HOURS = {int(form_data.get('heartbeat_interval_hours', 6))}
DAILY_REPORT_TIME = "{form_data.get('daily_report_time', '23:59')}"

# Kill Switch Settings
MAX_DRAWDOWN_PCT = {float(form_data.get('max_drawdown_pct', 12.0))}
MAX_API_FAILURES = {int(form_data.get('max_api_failures', 5))}
"""
        
        # Write to trading_config.py
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'trading_config.py')
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return {"status": "success", "message": "Configuration saved successfully!"}
        
    except Exception as e:
        return {"status": "error", "message": f"Error saving configuration: {str(e)}"}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page"""
    return templates.TemplateResponse("base.html", {"request": request})


@router.get("/strategy", response_class=HTMLResponse)
async def strategy_page(request: Request, db: Session = Depends(get_db)):
    """Strategy analysis page showing trading logic and decisions"""
    from ..config import settings
    import httpx
    import time
    import hmac
    import hashlib
    
    # Get current market data and analyze strategy
    strategy_analysis = []
    
    try:
        # Import trading configuration
        import sys
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.insert(0, project_root)
        
        from trading_config import TRADING_SYMBOL, TIMEFRAME
        
        # Get current market data
        if settings.MODE == "live":
            # Get live data from Binance
            try:
                # Get current price
                price_url = f"https://api.binance.com/api/v3/ticker/price?symbol={TRADING_SYMBOL}"
                with httpx.Client() as client:
                    price_response = client.get(price_url)
                    if price_response.status_code == 200:
                        current_price = float(price_response.json()['price'])
                    else:
                        current_price = 0.0
                
                # Get klines data for analysis
                klines_url = f"https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': TRADING_SYMBOL,
                    'interval': TIMEFRAME,
                    'limit': 100
                }
                
                with httpx.Client() as client:
                    klines_response = client.get(klines_url, params=params)
                    if klines_response.status_code == 200:
                        klines_data = klines_response.json()
                        
                        # Convert to DataFrame
                        df = pd.DataFrame(klines_data, columns=[
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_asset_volume', 'number_of_trades',
                            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                        ])
                        
                        # Convert to numeric
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            df[col] = pd.to_numeric(df[col])
                        
                        # Calculate indicators
                        df['ema20'] = df['close'].ewm(span=20).mean()
                        df['ema50'] = df['close'].ewm(span=50).mean()
                        
                        # Calculate RSI
                        delta = df['close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        df['rsi'] = 100 - (100 / (1 + rs))
                        
                        # Calculate ATR
                        high_low = df['high'] - df['low']
                        high_close = np.abs(df['high'] - df['close'].shift())
                        low_close = np.abs(df['low'] - df['close'].shift())
                        ranges = pd.concat([high_low, high_close, low_close], axis=1)
                        true_range = np.max(ranges, axis=1)
                        df['atr'] = true_range.rolling(14).mean()
                        
                        # Calculate EMA difference percentage
                        df['ema_diff_pct'] = abs(df['ema20'] - df['ema50']) / df['close']
                        
                        # Get latest values
                        latest = df.iloc[-1]
                        close = latest['close']
                        ema20 = latest['ema20']
                        ema50 = latest['ema50']
                        rsi = latest['rsi']
                        atr = latest['atr']
                        ema_diff_pct = latest['ema_diff_pct']
                        
                        # Analyze trading conditions
                        condition1 = close > ema20
                        condition2 = ema20 > ema50
                        condition3 = rsi > 50
                        in_chop = (ema_diff_pct < 0.003) and (45 <= rsi <= 55)
                        not_in_chop = not in_chop
                        
                        long_signal = condition1 and condition2 and condition3 and not_in_chop
                        
                        # Create strategy analysis
                        strategy_analysis = [
                            {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'market_data',
                                'message': f'Current {TRADING_SYMBOL} price: ${close:.2f}',
                                'status': 'info'
                            },
                            {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'indicator',
                                'message': f'EMA20: ${ema20:.2f}, EMA50: ${ema50:.2f}',
                                'status': 'info'
                            },
                            {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'indicator',
                                'message': f'RSI: {rsi:.1f}',
                                'status': 'info'
                            },
                            {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'indicator',
                                'message': f'ATR: ${atr:.4f}',
                                'status': 'info'
                            }
                        ]
                        
                        # Check each condition
                        if condition1:
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'condition',
                                'message': f'✅ Price (${close:.2f}) > EMA20 (${ema20:.2f}) - UPTREND CONFIRMED',
                                'status': 'success'
                            })
                        else:
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'condition',
                                'message': f'❌ Price (${close:.2f}) <= EMA20 (${ema20:.2f}) - NO UPTREND',
                                'status': 'danger'
                            })
                        
                        if condition2:
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'condition',
                                'message': f'✅ EMA20 (${ema20:.2f}) > EMA50 (${ema50:.2f}) - TREND ALIGNMENT GOOD',
                                'status': 'success'
                            })
                        else:
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'condition',
                                'message': f'❌ EMA20 (${ema20:.2f}) <= EMA50 (${ema50:.2f}) - TREND NOT ALIGNED',
                                'status': 'danger'
                            })
                        
                        if condition3:
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'condition',
                                'message': f'✅ RSI ({rsi:.1f}) > 50 - MOMENTUM POSITIVE',
                                'status': 'success'
                            })
                        else:
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'condition',
                                'message': f'❌ RSI ({rsi:.1f}) <= 50 - MOMENTUM WEAK',
                                'status': 'danger'
                            })
                        
                        if not_in_chop:
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'condition',
                                'message': f'✅ Not in choppy market (EMA diff: {ema_diff_pct:.4f}, RSI: {rsi:.1f}) - CLEAR TREND',
                                'status': 'success'
                            })
                        else:
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'condition',
                                'message': f'❌ In choppy market (EMA diff: {ema_diff_pct:.4f}, RSI: {rsi:.1f}) - AVOID TRADING',
                                'status': 'warning'
                            })
                        
                        # Final decision
                        if long_signal:
                            sl = close - 1.8 * atr
                            tp1 = close + 1.5 * atr
                            
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'decision',
                                'message': f'🎯 LONG SIGNAL GENERATED! Entry: ${close:.2f}, Stop Loss: ${sl:.2f}, Take Profit: ${tp1:.2f}',
                                'status': 'success'
                            })
                        else:
                            failed_conditions = []
                            if not condition1:
                                failed_conditions.append("Price not above EMA20")
                            if not condition2:
                                failed_conditions.append("EMA20 not above EMA50")
                            if not condition3:
                                failed_conditions.append("RSI below 50")
                            if in_chop:
                                failed_conditions.append("Market too choppy")
                            
                            strategy_analysis.append({
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'type': 'decision',
                                'message': f'⏸️ NO TRADE SIGNAL - Reasons: {", ".join(failed_conditions)}',
                                'status': 'warning'
                            })
                        
                    else:
                        strategy_analysis.append({
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'type': 'error',
                            'message': f'Failed to fetch market data for {TRADING_SYMBOL}',
                            'status': 'danger'
                        })
                        
            except Exception as e:
                strategy_analysis.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'error',
                    'message': f'Error analyzing market: {str(e)}',
                    'status': 'danger'
                })
        else:
            # Paper mode - show sample analysis
            strategy_analysis = [
                {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'info',
                    'message': '📊 Strategy Analysis (Paper Mode)',
                    'status': 'info'
                },
                {
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'info',
                    'message': 'Switch to LIVE mode to see real-time strategy analysis',
                    'status': 'info'
                }
            ]
            
    except Exception as e:
        strategy_analysis = [
            {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'error',
                'message': f'Error loading strategy analysis: {str(e)}',
                'status': 'danger'
            }
        ]
    
    # Get current SOL price for title
    current_sol_price = None
    try:
        with httpx.Client() as client:
            price_response = client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={'symbol': 'SOLUSDT'}
            )
            if price_response.status_code == 200:
                price_data = price_response.json()
                current_sol_price = float(price_data['price'])
    except Exception as e:
        # If price fetch fails, use None
        current_sol_price = None
    
    context = {
        "request": request,
        "strategy_analysis": strategy_analysis,
        "trading_symbol": TRADING_SYMBOL if 'TRADING_SYMBOL' in locals() else "SOLUSDT",
        "timeframe": TIMEFRAME if 'TIMEFRAME' in locals() else "15m",
        "mode": settings.MODE,
        "current_sol_price": current_sol_price
    }
    
    return templates.TemplateResponse("strategy.html", context)
