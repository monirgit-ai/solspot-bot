import httpx
import hmac
import hashlib
import time
import json
import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
from datetime import datetime
from binance.spot import Spot
import sys
import os
import uuid

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.app.config import settings
from api.app.db import SessionLocal
from api.app.repo import OrderRepository, TradeRepository, EquityRepository, AlertRepository

logger = logging.getLogger(__name__)


class SpotClient:
    """Unified spot trading client for paper and live modes"""
    
    def __init__(self, mode: str = "paper"):
        self.mode = mode
        self.base_url = "https://api.binance.com"
        self.testnet_url = "https://testnet.binance.vision"
        
        # Initialize Binance client for live mode
        if mode == "live":
            if not settings.BINANCE_API_KEY or not settings.BINANCE_API_SECRET:
                raise ValueError("Binance API credentials required for live mode")
            self.client = Spot(
                api_key=settings.BINANCE_API_KEY,
                api_secret=settings.BINANCE_API_SECRET,
                base_url=self.base_url
            )
        else:
            self.client = None
        
        # Paper trading state
        self.paper_balance = {
            'USDT': 1000.0,
            'SOL': 0.0
        }
        self.paper_orders = []
        self.order_id_counter = 1
        self.instance_id = str(uuid.uuid4())[:8]  # Unique instance identifier
        
        # Database session
        self.db = SessionLocal()
        self.order_repo = OrderRepository(self.db)
        self.trade_repo = TradeRepository(self.db)
        self.equity_repo = EquityRepository(self.db)
        self.alert_repo = AlertRepository(self.db)
    
    def __del__(self):
        """Cleanup database session"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def _get_unique_order_id(self) -> str:
        """Generate unique order ID"""
        order_id = f"{self.instance_id}_{self.order_id_counter}"
        self.order_id_counter += 1
        return order_id
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> pd.DataFrame:
        """Get kline/candlestick data"""
        try:
            if self.mode == "live":
                # Use Binance client for live mode
                klines = self.client.klines(symbol, interval, limit=limit)
            else:
                # Use public API for paper mode
                url = f"{self.base_url}/api/v3/klines"
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                
                with httpx.Client() as client:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    klines = response.json()
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convert to float
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get symbol information including stepSize and tickSize"""
        try:
            if self.mode == "live":
                # Use Binance client for live mode
                exchange_info = self.client.exchange_info()
            else:
                # Use public API for paper mode
                url = f"{self.base_url}/api/v3/exchangeInfo"
                
                with httpx.Client() as client:
                    response = client.get(url)
                    response.raise_for_status()
                    exchange_info = response.json()
            
            # Find symbol info
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    # Extract filters
                    step_size = 0.001  # Default
                    tick_size = 0.01   # Default
                    
                    for filter_info in s['filters']:
                        if filter_info['filterType'] == 'LOT_SIZE':
                            step_size = float(filter_info['stepSize'])
                        elif filter_info['filterType'] == 'PRICE_FILTER':
                            tick_size = float(filter_info['tickSize'])
                    
                    return {
                        'symbol': symbol,
                        'stepSize': step_size,
                        'tickSize': tick_size,
                        'status': s['status']
                    }
            
            return {'symbol': symbol, 'stepSize': 0.001, 'tickSize': 0.01, 'status': 'TRADING'}
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return {'symbol': symbol, 'stepSize': 0.001, 'tickSize': 0.01, 'status': 'TRADING'}
    
    def balances(self) -> Dict[str, float]:
        """Get account balances"""
        if self.mode == "live":
            try:
                account = self.client.account()
                balances = {}
                for balance in account['balances']:
                    if float(balance['free']) > 0 or float(balance['locked']) > 0:
                        balances[balance['asset']] = float(balance['free'])
                return balances
            except Exception as e:
                logger.error(f"Error getting live balances: {e}")
                return {}
        else:
            # Return paper trading balances
            return self.paper_balance.copy()
    
    def place_limit_buy(self, symbol: str, quantity: float, price: float) -> Dict:
        """Place a limit buy order"""
        try:
            if self.mode == "live":
                # Live trading
                order = self.client.new_order(
                    symbol=symbol,
                    side='BUY',
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=price
                )
                
                # Log to database
                self.order_repo.insert_order(
                    side='BUY',
                    symbol=symbol,
                    qty=quantity,
                    price=price,
                    order_type='LIMIT',
                    status=order['status'],
                    binance_order_id=order['orderId']
                )
                
                return order
                
            else:
                # Paper trading
                order_id = self._get_unique_order_id()
                
                # Check if we have enough USDT
                cost = quantity * price
                if cost > self.paper_balance['USDT']:
                    raise ValueError(f"Insufficient USDT balance. Need {cost}, have {self.paper_balance['USDT']}")
                
                # Simulate order placement
                order = {
                    'orderId': order_id,
                    'symbol': symbol,
                    'side': 'BUY',
                    'type': 'LIMIT',
                    'quantity': quantity,
                    'price': price,
                    'status': 'NEW',
                    'time': int(time.time() * 1000)
                }
                
                # Log to database
                self.order_repo.insert_order(
                    side='BUY',
                    symbol=symbol,
                    qty=quantity,
                    price=price,
                    order_type='LIMIT',
                    status='NEW',
                    binance_order_id=order_id
                )
                
                # Simulate immediate fill for paper trading
                self._simulate_fill(order, 'BUY', quantity, price)
                
                return order
                
        except Exception as e:
            logger.error(f"Error placing limit buy order: {e}")
            try:
                self.alert_repo.insert_alert('error', f"Limit buy order failed: {str(e)}")
            except:
                pass  # Don't fail if alert logging fails
            raise
    
    def place_limit_sell(self, symbol: str, quantity: float, price: float) -> Dict:
        """Place a limit sell order"""
        try:
            if self.mode == "live":
                # Live trading
                order = self.client.new_order(
                    symbol=symbol,
                    side='SELL',
                    type='LIMIT',
                    timeInForce='GTC',
                    quantity=quantity,
                    price=price
                )
                
                # Log to database
                self.order_repo.insert_order(
                    side='SELL',
                    symbol=symbol,
                    qty=quantity,
                    price=price,
                    order_type='LIMIT',
                    status=order['status'],
                    binance_order_id=order['orderId']
                )
                
                return order
                
            else:
                # Paper trading
                order_id = self._get_unique_order_id()
                
                # Check if we have enough SOL
                asset = symbol.replace('USDT', '')
                if quantity > self.paper_balance.get(asset, 0):
                    raise ValueError(f"Insufficient {asset} balance. Need {quantity}, have {self.paper_balance.get(asset, 0)}")
                
                # Simulate order placement
                order = {
                    'orderId': order_id,
                    'symbol': symbol,
                    'side': 'SELL',
                    'type': 'LIMIT',
                    'quantity': quantity,
                    'price': price,
                    'status': 'NEW',
                    'time': int(time.time() * 1000)
                }
                
                # Log to database
                self.order_repo.insert_order(
                    side='SELL',
                    symbol=symbol,
                    qty=quantity,
                    price=price,
                    order_type='LIMIT',
                    status='NEW',
                    binance_order_id=order_id
                )
                
                # Simulate immediate fill for paper trading
                self._simulate_fill(order, 'SELL', quantity, price)
                
                return order
                
        except Exception as e:
            logger.error(f"Error placing limit sell order: {e}")
            try:
                self.alert_repo.insert_alert('error', f"Limit sell order failed: {str(e)}")
            except:
                pass  # Don't fail if alert logging fails
            raise
    
    def place_market_sell(self, symbol: str, quantity: float) -> Dict:
        """Place a market sell order"""
        try:
            # Get current price for market orders
            current_price = self._get_current_price(symbol)
            
            if self.mode == "live":
                # Live trading
                order = self.client.new_order(
                    symbol=symbol,
                    side='SELL',
                    type='MARKET',
                    quantity=quantity
                )
                
                # Log to database
                self.order_repo.insert_order(
                    side='SELL',
                    symbol=symbol,
                    qty=quantity,
                    price=current_price,
                    order_type='MARKET',
                    status=order['status'],
                    binance_order_id=order['orderId']
                )
                
                return order
                
            else:
                # Paper trading
                order_id = self._get_unique_order_id()
                
                # Check if we have enough SOL
                asset = symbol.replace('USDT', '')
                if quantity > self.paper_balance.get(asset, 0):
                    raise ValueError(f"Insufficient {asset} balance. Need {quantity}, have {self.paper_balance.get(asset, 0)}")
                
                # Simulate order placement
                order = {
                    'orderId': order_id,
                    'symbol': symbol,
                    'side': 'SELL',
                    'type': 'MARKET',
                    'quantity': quantity,
                    'price': current_price,
                    'status': 'FILLED',
                    'time': int(time.time() * 1000)
                }
                
                # Log to database
                self.order_repo.insert_order(
                    side='SELL',
                    symbol=symbol,
                    qty=quantity,
                    price=current_price,
                    order_type='MARKET',
                    status='FILLED',
                    binance_order_id=order_id
                )
                
                # Simulate immediate fill for paper trading
                self._simulate_fill(order, 'SELL', quantity, current_price)
                
                return order
                
        except Exception as e:
            logger.error(f"Error placing market sell order: {e}")
            try:
                self.alert_repo.insert_alert('error', f"Market sell order failed: {str(e)}")
            except:
                pass  # Don't fail if alert logging fails
            raise
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        try:
            if self.mode == "live":
                ticker = self.client.ticker_price(symbol=symbol)
                return float(ticker['price'])
            else:
                # For paper trading, use a simulated price
                # In a real implementation, you'd get this from the klines data
                return 100.0  # Simulated price
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return 100.0  # Fallback price
    
    def _simulate_fill(self, order: Dict, side: str, quantity: float, price: float):
        """Simulate order fill for paper trading"""
        try:
            symbol = order['symbol']
            asset = symbol.replace('USDT', '')
            
            if side == 'BUY':
                # Buy: spend USDT, get SOL
                cost = quantity * price
                self.paper_balance['USDT'] -= cost
                self.paper_balance[asset] = self.paper_balance.get(asset, 0) + quantity
                
                # Log trade
                self.trade_repo.open_trade(
                    symbol=symbol,
                    qty=quantity,
                    entry_price=price,
                    sl=price * 0.95,  # 5% stop loss
                    tp1=price * 1.10   # 10% take profit
                )
                
                # Update equity
                total_equity = self.paper_balance['USDT'] + (self.paper_balance.get(asset, 0) * price)
                self.equity_repo.insert_snapshot(total_equity)
                
                logger.info(f"Paper BUY filled: {quantity} {asset} @ ${price}")
                
            else:  # SELL
                # Sell: spend SOL, get USDT
                proceeds = quantity * price
                self.paper_balance[asset] -= quantity
                self.paper_balance['USDT'] += proceeds
                
                # Close trade if exists
                open_trades = self.trade_repo.get_open_trades()
                for trade in open_trades:
                    if trade.symbol == symbol:
                        self.trade_repo.close_trade(trade.id, price, "Market sell")
                        break
                
                # Update equity
                total_equity = self.paper_balance['USDT'] + (self.paper_balance.get(asset, 0) * price)
                self.equity_repo.insert_snapshot(total_equity)
                
                logger.info(f"Paper SELL filled: {quantity} {asset} @ ${price}")
            
            # Log alert
            try:
                self.alert_repo.insert_alert(
                    'info', 
                    f"Paper {side} order filled: {quantity} {asset} @ ${price:.2f}"
                )
            except:
                pass  # Don't fail if alert logging fails
            
        except Exception as e:
            logger.error(f"Error simulating fill: {e}")
            try:
                self.alert_repo.insert_alert('error', f"Paper fill simulation failed: {str(e)}")
            except:
                pass  # Don't fail if alert logging fails
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        if self.mode == "live":
            try:
                return self.client.account()
            except Exception as e:
                logger.error(f"Error getting live account info: {e}")
                return {}
        else:
            # Return paper account info
            total_equity = sum(self.paper_balance.values())
            return {
                'accountType': 'SPOT',
                'balances': [
                    {'asset': asset, 'free': str(amount), 'locked': '0.00000000'}
                    for asset, amount in self.paper_balance.items()
                ],
                'totalEquity': total_equity
            }


# Legacy classes for backward compatibility
class BinanceSpotAPI:
    """Legacy Binance Spot API wrapper"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, testnet: bool = True):
        self.client = SpotClient(mode="live" if not testnet else "paper")
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> List[List]:
        """Get kline/candlestick data"""
        df = self.client.get_klines(symbol, interval, limit)
        # Convert DataFrame back to list format for compatibility
        return df.reset_index().values.tolist()
    
    def get_symbol_price(self, symbol: str) -> Dict:
        """Get current price for symbol"""
        price = self.client._get_current_price(symbol)
        return {'price': str(price)}


class PaperTradingAPI:
    """Legacy Paper trading implementation"""
    
    def __init__(self, initial_balance: float = 20.0):
        self.client = SpotClient(mode="paper")
        self.client.paper_balance['USDT'] = initial_balance
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> List[List]:
        """Get kline/candlestick data"""
        df = self.client.get_klines(symbol, interval, limit)
        # Convert DataFrame back to list format for compatibility
        return df.reset_index().values.tolist()
    
    def get_symbol_price(self, symbol: str) -> Dict:
        """Get current price for symbol"""
        price = self.client._get_current_price(symbol)
        return {'price': str(price)}
