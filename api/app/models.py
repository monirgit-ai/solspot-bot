from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, CheckConstraint
from sqlalchemy.sql import func
from .db import Base


class Setting(Base):
    __tablename__ = "settings"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=False)


class EquitySnapshot(Base):
    __tablename__ = "equity_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    equity_usdt = Column(Float, nullable=False)
    
    __table_args__ = (
        CheckConstraint('equity_usdt >= 0', name='check_equity_positive'),
    )


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    side = Column(String, nullable=False)
    symbol = Column(String, nullable=False, index=True)
    qty = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # MARKET, LIMIT, etc.
    status = Column(String, nullable=False)  # PENDING, FILLED, CANCELLED, etc.
    binance_order_id = Column(String, nullable=True, unique=True, index=True)
    
    __table_args__ = (
        CheckConstraint("side IN ('BUY','SELL')", name='check_valid_side'),
        CheckConstraint('qty > 0', name='check_positive_qty'),
        CheckConstraint('price > 0', name='check_positive_price'),
    )


class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    entry_ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    exit_ts = Column(DateTime(timezone=True), nullable=True)
    symbol = Column(String, nullable=False, index=True)
    qty = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    sl = Column(Float, nullable=False)  # Stop loss
    tp1 = Column(Float, nullable=False)  # Take profit 1
    trail_mult = Column(Float, nullable=True)  # Trailing stop multiplier
    pnl_usdt = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    reason_exit = Column(String, nullable=True)
    
    __table_args__ = (
        CheckConstraint('qty > 0', name='check_positive_qty'),
        CheckConstraint('entry_price > 0', name='check_positive_entry_price'),
        CheckConstraint('sl > 0', name='check_positive_sl'),
        CheckConstraint('tp1 > 0', name='check_positive_tp1'),
    )


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    __table_args__ = (
        CheckConstraint("level IN ('info','warn','error')", name='check_valid_level'),
    )
