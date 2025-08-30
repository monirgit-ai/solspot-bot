from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, date
from sqlalchemy import func, desc, and_
from ..db import get_db
from ..repo import TradeRepository, OrderRepository, EquityRepository, AlertRepository, SettingRepository
from .. import models

router = APIRouter()

@router.get("/trades")
async def get_trades(limit: int = 10, db: Session = Depends(get_db)):
    trade_repo = TradeRepository(db)
    trades = trade_repo.recent_trades(limit=limit)
    return trades

@router.get("/trades/open")
async def get_open_trades(db: Session = Depends(get_db)):
    trade_repo = TradeRepository(db)
    trades = trade_repo.get_open_trades()
    return trades

@router.get("/trades/summary")
async def get_trade_summary(db: Session = Depends(get_db)):
    trade_repo = TradeRepository(db)
    summary = trade_repo.get_trade_summary()
    return summary

@router.get("/trades/daily-pnl")
async def get_daily_pnl(period: str = "14d", db: Session = Depends(get_db)):
    """Get daily P&L for the specified period"""
    try:
        # Calculate start date based on period
        if period == "7d":
            start_date = date.today() - timedelta(days=7)
        elif period == "14d":
            start_date = date.today() - timedelta(days=14)
        elif period == "30d":
            start_date = date.today() - timedelta(days=30)
        else:
            start_date = date.today() - timedelta(days=14)
        
        # Query daily P&L
        daily_pnl = db.query(
            func.date(models.Trade.exit_ts).label('date'),
            func.sum(models.Trade.pnl_usdt).label('pnl')
        ).filter(
            and_(
                models.Trade.exit_ts.isnot(None),
                models.Trade.exit_ts >= start_date
            )
        ).group_by(
            func.date(models.Trade.exit_ts)
        ).order_by(
            func.date(models.Trade.exit_ts)
        ).all()
        
        return [
            {
                "date": str(item.date),
                "pnl": float(item.pnl) if item.pnl else 0.0
            }
            for item in daily_pnl
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching daily P&L: {str(e)}")

@router.get("/orders")
async def get_orders(limit: int = 10, db: Session = Depends(get_db)):
    order_repo = OrderRepository(db)
    orders = order_repo.recent_orders(limit=limit)
    return orders

@router.get("/equity/latest")
async def get_latest_equity(db: Session = Depends(get_db)):
    equity_repo = EquityRepository(db)
    equity = equity_repo.latest_equity()
    return equity

@router.get("/equity/today")
async def get_today_equity(db: Session = Depends(get_db)):
    equity_repo = EquityRepository(db)
    metrics = equity_repo.today_metrics()
    return metrics

@router.get("/equity/history")
async def get_equity_history(period: str = "30d", db: Session = Depends(get_db)):
    """Get equity history for the specified period"""
    try:
        # Calculate start date based on period
        if period == "7d":
            start_date = datetime.now() - timedelta(days=7)
        elif period == "30d":
            start_date = datetime.now() - timedelta(days=30)
        elif period == "90d":
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        # Query equity history
        equity_history = db.query(models.EquitySnapshot).filter(
            models.EquitySnapshot.ts >= start_date
        ).order_by(
            models.EquitySnapshot.ts
        ).all()
        
        return [
            {
                "ts": item.ts.isoformat(),
                "equity_usdt": float(item.equity_usdt)
            }
            for item in equity_history
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching equity history: {str(e)}")

@router.get("/alerts")
async def get_alerts(limit: int = 10, db: Session = Depends(get_db)):
    alert_repo = AlertRepository(db)
    alerts = alert_repo.get_recent_alerts(limit=limit)
    return alerts

@router.get("/settings/{key}")
async def get_setting(key: str, db: Session = Depends(get_db)):
    setting_repo = SettingRepository(db)
    value = setting_repo.get_setting(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting {key} not found")
    return {"key": key, "value": value}

@router.post("/settings/{key}")
async def set_setting(key: str, value: str, db: Session = Depends(get_db)):
    setting_repo = SettingRepository(db)
    setting = setting_repo.set_setting(key, value)
    return setting

@router.get("/price/{symbol}")
async def get_current_price(symbol: str, db: Session = Depends(get_db)):
    """Get current price for a symbol"""
    try:
        from ..config import settings
        
        if settings.MODE == "live":
            # Use real Binance API for live mode
            import httpx
            
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': symbol}
            
            with httpx.Client() as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "symbol": data['symbol'],
                    "price": float(data['price']),
                    "timestamp": datetime.now().isoformat(),
                    "source": "binance_live"
                }
        else:
            # Use public API for paper mode (no API key required)
            import httpx
            
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': symbol}
            
            with httpx.Client() as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "symbol": data['symbol'],
                    "price": float(data['price']),
                    "timestamp": datetime.now().isoformat(),
                    "source": "binance_public"
                }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price: {str(e)}")

@router.get("/account")
async def get_account_info(db: Session = Depends(get_db)):
    """Get account information (real balance in live mode)"""
    try:
        from ..config import settings
        
        if settings.MODE == "live":
            # Use real Binance API for live mode
            import httpx
            import time
            import hmac
            import hashlib
            
            # Create signature for authenticated request
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
                data = response.json()
                
                # Filter out zero balances and format
                balances = [
                    {
                        'asset': balance['asset'],
                        'free': float(balance['free']),
                        'locked': float(balance['locked'])
                    }
                    for balance in data.get('balances', [])
                    if float(balance['free']) > 0 or float(balance['locked']) > 0
                ]
                
                return {
                    "accountType": data.get('accountType', 'SPOT'),
                    "balances": balances,
                    "permissions": data.get('permissions', []),
                    "timestamp": datetime.now().isoformat(),
                    "source": "binance_live"
                }
        else:
            # Return paper account info
            return {
                "accountType": "SPOT",
                "balances": [
                    {"asset": "USDT", "free": 1000.0, "locked": 0.0},
                    {"asset": "SOL", "free": 0.0, "locked": 0.0}
                ],
                "permissions": ["SPOT"],
                "timestamp": datetime.now().isoformat(),
                "source": "paper_mode"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching account info: {str(e)}")


# Bot Control Endpoints
@router.get("/bot/status")
async def get_bot_status(db: Session = Depends(get_db)):
    """Get bot status (running/paused)"""
    try:
        setting_repo = SettingRepository(db)
        is_paused = setting_repo.get_setting('is_paused') == 'true'
        
        return {
            "is_paused": is_paused,
            "is_running": not is_paused,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting bot status: {str(e)}")


@router.post("/bot/pause")
async def pause_bot(db: Session = Depends(get_db)):
    """Pause the trading bot"""
    try:
        setting_repo = SettingRepository(db)
        alert_repo = AlertRepository(db)
        
        # Set pause flag
        setting_repo.set_setting('is_paused', 'true')
        
        # Log alert
        alert_repo.insert_alert('info', 'Bot paused via web interface')
        
        # Send Telegram notification
        try:
            from ..telegram_webhook import tg_send
            from ..config import settings
            if settings.TG_BOT_TOKEN and settings.TG_CHAT_ID:
                await tg_send("⏸️ <b>Bot Paused</b>\n\nBot has been paused via web interface", int(settings.TG_CHAT_ID))
        except Exception as e:
            print(f"Failed to send Telegram notification: {e}")
        
        return {
            "status": "success",
            "message": "Bot paused successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error pausing bot: {str(e)}")


@router.post("/bot/resume")
async def resume_bot(db: Session = Depends(get_db)):
    """Resume the trading bot"""
    try:
        setting_repo = SettingRepository(db)
        alert_repo = AlertRepository(db)
        
        # Clear pause flag
        setting_repo.set_setting('is_paused', 'false')
        
        # Log alert
        alert_repo.insert_alert('info', 'Bot resumed via web interface')
        
        # Send Telegram notification
        try:
            from ..telegram_webhook import tg_send
            from ..config import settings
            if settings.TG_BOT_TOKEN and settings.TG_CHAT_ID:
                await tg_send("▶️ <b>Bot Resumed</b>\n\nBot has been resumed via web interface", int(settings.TG_CHAT_ID))
        except Exception as e:
            print(f"Failed to send Telegram notification: {e}")
        
        return {
            "status": "success",
            "message": "Bot resumed successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resuming bot: {str(e)}")
