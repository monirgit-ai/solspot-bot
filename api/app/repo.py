from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional, Dict
from datetime import datetime, date
from . import models


class SettingRepository:
    def __init__(self, db: Session):
        self.db = db
        self._bootstrap_defaults()
    
    def _bootstrap_defaults(self):
        """Bootstrap default settings if they don't exist"""
        defaults = {
            'risk_per_trade_pct': '0.5',
            'daily_loss_stop_pct': '1.5',
            'cooldown_bars': '1',
            'is_paused': 'false'
        }
        
        for key, value in defaults.items():
            existing = self.db.query(models.Setting).filter(models.Setting.key == key).first()
            if not existing:
                setting = models.Setting(key=key, value=value)
                self.db.add(setting)
        
        self.db.commit()
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get setting value by key"""
        setting = self.db.query(models.Setting).filter(models.Setting.key == key).first()
        return setting.value if setting else None
    
    def set_setting(self, key: str, value: str) -> models.Setting:
        """Set setting value by key"""
        setting = self.db.query(models.Setting).filter(models.Setting.key == key).first()
        if setting:
            setting.value = value
        else:
            setting = models.Setting(key=key, value=value)
            self.db.add(setting)
        
        self.db.commit()
        self.db.refresh(setting)
        return setting


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def insert_alert(self, level: str, message: str) -> models.Alert:
        """Insert a new alert"""
        alert = models.Alert(level=level, message=message)
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def get_recent_alerts(self, limit: int = 50) -> List[models.Alert]:
        """Get recent alerts"""
        return self.db.query(models.Alert).order_by(desc(models.Alert.ts)).limit(limit).all()
    
    def get_alerts_by_level(self, level: str, limit: int = 50) -> List[models.Alert]:
        """Get alerts by level"""
        return self.db.query(models.Alert).filter(
            models.Alert.level == level
        ).order_by(desc(models.Alert.ts)).limit(limit).all()


class EquityRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def insert_snapshot(self, equity_usdt: float) -> models.EquitySnapshot:
        """Insert equity snapshot"""
        snapshot = models.EquitySnapshot(equity_usdt=equity_usdt)
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot
    
    def latest_equity(self) -> Optional[models.EquitySnapshot]:
        """Get latest equity snapshot"""
        return self.db.query(models.EquitySnapshot).order_by(
            desc(models.EquitySnapshot.ts)
        ).first()
    
    def today_metrics(self) -> Dict:
        """Get today's trading metrics"""
        today = date.today()
        
        # Get today's snapshots
        today_snapshots = self.db.query(models.EquitySnapshot).filter(
            func.date(models.EquitySnapshot.ts) == today
        ).order_by(models.EquitySnapshot.ts).all()
        
        if not today_snapshots:
            return {
                'start_equity': 0,
                'current_equity': 0,
                'daily_pnl': 0,
                'daily_pnl_pct': 0,
                'snapshots_count': 0
            }
        
        start_equity = today_snapshots[0].equity_usdt
        current_equity = today_snapshots[-1].equity_usdt
        daily_pnl = current_equity - start_equity
        daily_pnl_pct = (daily_pnl / start_equity * 100) if start_equity > 0 else 0
        
        return {
            'start_equity': start_equity,
            'current_equity': current_equity,
            'daily_pnl': daily_pnl,
            'daily_pnl_pct': daily_pnl_pct,
            'snapshots_count': len(today_snapshots)
        }


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def insert_order(self, side: str, symbol: str, qty: float, price: float, 
                    order_type: str, status: str, binance_order_id: str = None) -> models.Order:
        """Insert a new order"""
        order = models.Order(
            side=side,
            symbol=symbol,
            qty=qty,
            price=price,
            type=order_type,
            status=status,
            binance_order_id=binance_order_id
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def update_order_status(self, order_id: int, status: str) -> Optional[models.Order]:
        """Update order status"""
        order = self.db.query(models.Order).filter(models.Order.id == order_id).first()
        if order:
            order.status = status
            self.db.commit()
            self.db.refresh(order)
        return order
    
    def recent_orders(self, limit: int = 20) -> List[models.Order]:
        """Get recent orders"""
        return self.db.query(models.Order).order_by(desc(models.Order.ts)).limit(limit).all()
    
    def get_orders_by_symbol(self, symbol: str, limit: int = 20) -> List[models.Order]:
        """Get orders by symbol"""
        return self.db.query(models.Order).filter(
            models.Order.symbol == symbol
        ).order_by(desc(models.Order.ts)).limit(limit).all()


class TradeRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def open_trade(self, symbol: str, qty: float, entry_price: float, 
                   sl: float, tp1: float, trail_mult: float = None) -> models.Trade:
        """Open a new trade"""
        trade = models.Trade(
            symbol=symbol,
            qty=qty,
            entry_price=entry_price,
            sl=sl,
            tp1=tp1,
            trail_mult=trail_mult
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade
    
    def close_trade(self, trade_id: int, exit_price: float, reason_exit: str) -> Optional[models.Trade]:
        """Close a trade"""
        trade = self.db.query(models.Trade).filter(models.Trade.id == trade_id).first()
        if trade and not trade.exit_ts:
            trade.exit_ts = datetime.now()
            trade.exit_price = exit_price
            trade.reason_exit = reason_exit
            
            # Calculate P&L
            if trade.entry_price > 0:
                pnl_usdt = (exit_price - trade.entry_price) * trade.qty
                pnl_pct = (pnl_usdt / (trade.entry_price * trade.qty)) * 100
                trade.pnl_usdt = pnl_usdt
                trade.pnl_pct = pnl_pct
            
            self.db.commit()
            self.db.refresh(trade)
        return trade
    
    def get_open_trades(self) -> List[models.Trade]:
        """Get all open trades (no exit_ts)"""
        return self.db.query(models.Trade).filter(
            models.Trade.exit_ts.is_(None)
        ).order_by(models.Trade.entry_ts).all()
    
    def recent_trades(self, limit: int = 20) -> List[models.Trade]:
        """Get recent trades"""
        return self.db.query(models.Trade).order_by(desc(models.Trade.entry_ts)).limit(limit).all()
    
    def get_trades_by_symbol(self, symbol: str, limit: int = 20) -> List[models.Trade]:
        """Get trades by symbol"""
        return self.db.query(models.Trade).filter(
            models.Trade.symbol == symbol
        ).order_by(desc(models.Trade.entry_ts)).limit(limit).all()
    
    def get_trades_by_date(self, trade_date: date) -> List[models.Trade]:
        """Get trades for a specific date"""
        start_datetime = datetime.combine(trade_date, datetime.min.time())
        end_datetime = datetime.combine(trade_date, datetime.max.time())
        
        return self.db.query(models.Trade).filter(
            and_(
                models.Trade.entry_ts >= start_datetime,
                models.Trade.entry_ts <= end_datetime
            )
        ).order_by(desc(models.Trade.entry_ts)).all()

    def get_trade_summary(self) -> Dict:
        """Get trading summary statistics"""
        total_trades = self.db.query(models.Trade).count()
        open_trades = self.db.query(models.Trade).filter(models.Trade.exit_ts.is_(None)).count()
        closed_trades = total_trades - open_trades
        
        # Calculate total P&L
        total_pnl = self.db.query(func.sum(models.Trade.pnl_usdt)).filter(
            models.Trade.pnl_usdt.isnot(None)
        ).scalar() or 0
        
        # Calculate win rate
        winning_trades = self.db.query(models.Trade).filter(
            models.Trade.pnl_usdt > 0
        ).count()
        
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'open_trades': open_trades,
            'closed_trades': closed_trades,
            'total_pnl': total_pnl,
            'winning_trades': winning_trades,
            'win_rate': win_rate
        }
