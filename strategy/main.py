import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import sys
import os
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.app.config import settings
from api.app.db import SessionLocal
from api.app.repo import TradeRepository, SettingRepository, EquityRepository, AlertRepository
from .exchange import SpotClient
from .indicators import calculate_all_indicators
from .signal import generate_signal
from .risk import RiskManager

logger = logging.getLogger(__name__)

class TradingBot:
    """Main trading bot implementation"""

    def __init__(self, symbol: str = None, interval: str = None):
        # Import trading configuration
        try:
            from trading_config import (
                TRADING_SYMBOL, TIMEFRAME, INITIAL_EQUITY, RISK_PER_TRADE_PCT,
                DAILY_LOSS_STOP_PCT, COOLDOWN_BARS, MAX_DRAWDOWN_PCT, MAX_API_FAILURES
            )
            self.symbol = symbol or TRADING_SYMBOL
            self.interval = interval or TIMEFRAME
            self.initial_equity = INITIAL_EQUITY
            self.risk_pct = RISK_PER_TRADE_PCT
            self.daily_stop_pct = DAILY_LOSS_STOP_PCT
            self.cooldown_bars = COOLDOWN_BARS
            self.max_drawdown_pct = MAX_DRAWDOWN_PCT
            self.max_api_failures = MAX_API_FAILURES
        except ImportError:
            # Fallback to default values if config file doesn't exist
            self.symbol = symbol or "SOLUSDT"
            self.interval = interval or "15m"
            self.initial_equity = 10000.0
            self.risk_pct = 0.005
            self.daily_stop_pct = 0.015
            self.cooldown_bars = 1
            self.max_drawdown_pct = 12.0
            self.max_api_failures = 5

        self.mode = settings.MODE
        self.tz = settings.TZ

        self.exchange = SpotClient(mode=self.mode)
        self.db = SessionLocal()
        self.trade_repo = TradeRepository(self.db)
        self.setting_repo = SettingRepository(self.db)
        self.equity_repo = EquityRepository(self.db)
        self.alert_repo = AlertRepository(self.db)

        self.risk_manager = RiskManager(
            initial_equity=self.initial_equity,
            risk_per_trade_pct=self.risk_pct,
            daily_loss_stop_pct=self.daily_stop_pct,
            cooldown_bars=self.cooldown_bars
        )

        self.last_bar_time = None
        self.current_bar = 0
        self.is_running = False
        
        # Kill switch tracking
        self.peak_equity = self.initial_equity
        self.api_failure_count = 0
        
        # Initialize scheduler
        self.scheduler = AsyncIOScheduler(timezone=self.tz)
        self.setup_scheduler()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
        if hasattr(self, 'scheduler'):
            self.scheduler.shutdown()

    def setup_scheduler(self):
        """Setup scheduled tasks"""
        try:
            # Daily report at 23:59 Asia/Dhaka
            self.scheduler.add_job(
                self.send_daily_report,
                CronTrigger(hour=23, minute=59, timezone=self.tz),
                id='daily_report',
                name='Daily Trading Report',
                replace_existing=True
            )
            
            # Heartbeat every 6 hours
            self.scheduler.add_job(
                self.send_heartbeat,
                CronTrigger(hour='*/6', timezone=self.tz),
                id='heartbeat',
                name='Bot Heartbeat',
                replace_existing=True
            )
            
            # Kill switch check every 15 minutes
            self.scheduler.add_job(
                self.check_kill_switches,
                CronTrigger(minute='*/15', timezone=self.tz),
                id='kill_switch_check',
                name='Kill Switch Check',
                replace_existing=True
            )
            
            logger.info("Scheduler setup complete")
            logger.info(f"Daily report scheduled for 23:59 {self.tz}")
            logger.info(f"Heartbeat scheduled every 6 hours {self.tz}")
            logger.info(f"Kill switch check every 15 minutes {self.tz}")
            
        except Exception as e:
            logger.error(f"Error setting up scheduler: {e}")

    async def check_kill_switches(self):
        """Check all kill switches and pause if needed"""
        try:
            logger.debug("Checking kill switches...")
            
            # Get current equity and metrics
            latest_equity = self.equity_repo.latest_equity()
            today_metrics = self.equity_repo.today_metrics()
            current_equity = latest_equity.equity_usdt if latest_equity else 10000.0
            
            # Update peak equity if higher
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
                logger.info(f"New peak equity: ${self.peak_equity:,.2f}")
            
            # 1. Daily Loss Stop Kill Switch
            daily_loss_stop_pct = float(self.setting_repo.get_setting('daily_loss_stop_pct') or '0.015')
            daily_loss_limit = self.peak_equity * daily_loss_stop_pct
            
            if today_metrics and today_metrics['daily_pnl'] < -daily_loss_limit:
                await self.trigger_kill_switch(
                    "Daily Loss Stop",
                    f"Daily P&L (${today_metrics['daily_pnl']:,.2f}) exceeded limit (${-daily_loss_limit:,.2f})"
                )
                return
            
            # 2. Max Drawdown Kill Switch
            if self.peak_equity > 0:
                current_drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100
                
                if current_drawdown_pct >= self.max_drawdown_pct:
                    await self.trigger_kill_switch(
                        "Max Drawdown",
                        f"Drawdown ({current_drawdown_pct:.1f}%) exceeded limit ({self.max_drawdown_pct}%)"
                    )
                    return
            
            # 3. API Health Kill Switch
            if self.api_failure_count >= self.max_api_failures:
                await self.trigger_kill_switch(
                    "API Health",
                    f"API failures ({self.api_failure_count}) exceeded limit ({self.max_api_failures})"
                )
                return
            
            # Reset API failure count if we're healthy
            if self.api_failure_count > 0:
                logger.info(f"API health recovered, resetting failure count from {self.api_failure_count}")
                self.api_failure_count = 0
                
        except Exception as e:
            logger.error(f"Error checking kill switches: {e}")

    async def trigger_kill_switch(self, switch_type: str, reason: str):
        """Trigger a kill switch and pause trading"""
        try:
            logger.warning(f"KILL SWITCH TRIGGERED: {switch_type} - {reason}")
            
            # Pause trading
            self.setting_repo.set_setting('is_paused', 'true')
            
            # Send Telegram alert
            message = f"""
🚨 <b>KILL SWITCH ACTIVATED</b>
⚠️ {switch_type}

📊 <b>Current Status</b>
• Equity: ${self.equity_repo.latest_equity().equity_usdt:,.2f}
• Peak Equity: ${self.peak_equity:,.2f}
• Today's P&L: ${self.equity_repo.today_metrics()['daily_pnl']:,.2f}

🔍 <b>Reason</b>
{reason}

🛑 <b>Action Taken</b>
• Trading PAUSED
• Manual intervention required
• Use /resume to restart (after investigation)

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')} {self.tz}
            """.strip()
            
            await self.tg_send(message)
            
            # Log alert
            self.alert_repo.insert_alert(
                'error',
                f"Kill switch triggered: {switch_type} - {reason}"
            )
            
            logger.error(f"Trading paused due to kill switch: {switch_type}")
            
        except Exception as e:
            logger.error(f"Error triggering kill switch: {e}")

    def record_api_failure(self):
        """Record an API failure"""
        self.api_failure_count += 1
        logger.warning(f"API failure recorded. Count: {self.api_failure_count}/{self.max_api_failures}")
        
        if self.api_failure_count >= self.max_api_failures:
            logger.error(f"API failure limit reached ({self.api_failure_count})")
            asyncio.create_task(self.check_kill_switches())

    def record_api_success(self):
        """Record successful API call"""
        if self.api_failure_count > 0:
            logger.info(f"API success recorded. Resetting failure count from {self.api_failure_count}")
            self.api_failure_count = 0

    async def tg_send(self, message: str) -> bool:
        """Send message via Telegram"""
        try:
            if not settings.TG_BOT_TOKEN or not settings.TG_CHAT_ID:
                logger.warning("Telegram credentials not configured")
                return False
                
            import httpx
            url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": settings.TG_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=data, timeout=10.0)
                if response.status_code == 200:
                    logger.info("Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    async def send_daily_report(self):
        """Send daily trading report"""
        try:
            logger.info("Generating daily report...")
            
            # Get today's metrics
            today_metrics = self.equity_repo.today_metrics()
            latest_equity = self.equity_repo.latest_equity()
            
            # Get today's trades
            today_trades = self.trade_repo.get_trades_by_date(datetime.now().date())
            closed_trades = [t for t in today_trades if t.exit_ts is not None]
            
            # Calculate metrics
            total_trades = len(closed_trades)
            winning_trades = len([t for t in closed_trades if t.pnl_usdt and t.pnl_usdt > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            total_pnl = sum(t.pnl_usdt for t in closed_trades if t.pnl_usdt)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            # Get open positions
            open_trades = self.trade_repo.get_open_trades()
            open_positions = len(open_trades)
            
            # Calculate drawdown
            current_equity = latest_equity.equity_usdt if latest_equity else 10000.0
            drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity * 100) if self.peak_equity > 0 else 0
            
            # Format message
            message = f"""
📊 <b>Daily Trading Report</b>
📅 {datetime.now().strftime('%Y-%m-%d')}

💰 <b>Equity</b>
• Current: ${current_equity:,.2f}
• Peak: ${self.peak_equity:,.2f}
• Drawdown: {drawdown_pct:.1f}%
• Today's P&L: ${today_metrics['daily_pnl']:,.2f}

📈 <b>Trading Summary</b>
• Total Trades: {total_trades}
• Win Rate: {win_rate:.1f}%
• Total P&L: ${total_pnl:,.2f}
• Avg P&L: ${avg_pnl:,.2f}

🔄 <b>Open Positions</b>
• Count: {open_positions}
• Symbols: {', '.join([t.symbol for t in open_trades]) if open_trades else 'None'}

⚙️ <b>Bot Status</b>
• Mode: {self.mode.upper()}
• Paused: {'Yes' if self.is_paused() else 'No'}
• API Failures: {self.api_failure_count}/{self.max_api_failures}
            """.strip()
            
            # Send report
            success = await self.tg_send(message)
            if success:
                logger.info("Daily report sent successfully")
                # Log alert
                self.alert_repo.insert_alert('info', f"Daily report sent: {total_trades} trades, ${total_pnl:,.2f} P&L")
            else:
                logger.error("Failed to send daily report")
                
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")

    async def send_heartbeat(self):
        """Send heartbeat message"""
        try:
            logger.info("Sending heartbeat...")
            
            # Get current status
            latest_equity = self.equity_repo.latest_equity()
            is_paused = self.is_paused()
            open_trades = self.trade_repo.get_open_trades()
            
            # Get last trade
            recent_trades = self.trade_repo.recent_trades(limit=1)
            last_trade = recent_trades[0] if recent_trades else None
            
            # Calculate drawdown
            current_equity = latest_equity.equity_usdt if latest_equity else 10000.0
            drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity * 100) if self.peak_equity > 0 else 0
            
            # Format message
            message = f"""
💓 <b>Bot Heartbeat</b>
🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')} {self.tz}

⚙️ <b>Status</b>
• Mode: {self.mode.upper()}
• Paused: {'Yes' if is_paused else 'No'}
• Running: {'Yes' if self.is_running else 'No'}

💰 <b>Equity</b>
• Current: ${current_equity:,.2f}
• Peak: ${self.peak_equity:,.2f}
• Drawdown: {drawdown_pct:.1f}%

📊 <b>Positions</b>
• Open: {len(open_trades)}
• Symbols: {', '.join([t.symbol for t in open_trades]) if open_trades else 'None'}

🔄 <b>Last Trade</b>
{f"• {last_trade.symbol} - {last_trade.entry_ts.strftime('%H:%M')} - ${last_trade.entry_price:.2f}" if last_trade else "• No trades yet"}

🔧 <b>Health</b>
• API Failures: {self.api_failure_count}/{self.max_api_failures}
            """.strip()
            
            # Send heartbeat
            success = await self.tg_send(message)
            if success:
                logger.info("Heartbeat sent successfully")
            else:
                logger.error("Failed to send heartbeat")
                
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")

    def is_paused(self) -> bool:
        """Check if bot is paused"""
        try:
            is_paused_setting = self.setting_repo.get_setting('is_paused')
            return is_paused_setting == 'true'
        except Exception as e:
            logger.error(f"Error checking pause status: {e}")
            return False

    def get_open_trades(self) -> list:
        """Get open trades"""
        try:
            return self.trade_repo.get_open_trades()
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []

    def update_equity(self) -> None:
        """Update equity snapshot"""
        try:
            balances = self.exchange.balances()
            total_equity = balances.get('USDT', 0.0)
            
            # Add value of crypto holdings
            for symbol, qty in balances.items():
                if symbol != 'USDT' and qty > 0:
                    try:
                        # Get current price for the symbol
                        symbol_info = self.exchange.get_symbol_info(f"{symbol}USDT")
                        if symbol_info:
                            # Estimate value (simplified)
                            total_equity += qty * 200  # Rough estimate for SOL
                    except:
                        pass
            
            self.equity_repo.insert_snapshot(total_equity)
            self.risk_manager.update_equity(total_equity)
            
            # Update peak equity if higher
            if total_equity > self.peak_equity:
                self.peak_equity = total_equity
                logger.info(f"New peak equity: ${self.peak_equity:,.2f}")
            
            logger.info(f"Equity updated: ${total_equity:,.2f}")
            
        except Exception as e:
            logger.error(f"Error updating equity: {e}")
            self.record_api_failure()

    def detect_new_bar(self, df: 'pd.DataFrame') -> bool:
        """Detect if we have a new bar"""
        try:
            if df.empty:
                return False
                
            # Since timestamp is the index, we need to access it differently
            latest_time = df.index[-1]
            if isinstance(latest_time, str):
                latest_time = datetime.fromisoformat(latest_time.replace('Z', '+00:00'))
            
            if self.last_bar_time is None or latest_time > self.last_bar_time:
                self.last_bar_time = latest_time
                self.current_bar += 1
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error detecting new bar: {e}")
            return False

    def manage_exits(self) -> None:
        """Manage trade exits"""
        try:
            open_trades = self.get_open_trades()
            for trade in open_trades:
                # Get current price
                try:
                    current_price = self.exchange._get_current_price(trade.symbol)
                except:
                    continue
                
                # Check stop loss
                if current_price <= trade.sl:
                    self._close_trade(trade, trade.sl, "Stop Loss")
                    continue
                
                # Check take profit 1
                if current_price >= trade.tp1:
                    self._close_trade(trade, trade.tp1, "Take Profit 1")
                    continue
                
                # Check trailing stop (if enabled)
                if trade.trail_mult:
                    # Calculate trailing stop
                    trail_stop = current_price * (1 - trade.trail_mult)
                    if current_price <= trail_stop:
                        self._close_trade(trade, current_price, "Trailing Stop")
                        continue
                        
        except Exception as e:
            logger.error(f"Error managing exits: {e}")

    def _close_trade(self, trade, exit_price: float, reason: str) -> None:
        """Close a trade"""
        try:
            # Calculate P&L
            pnl_usdt = (exit_price - trade.entry_price) * trade.qty
            pnl_pct = (exit_price - trade.entry_price) / trade.entry_price * 100
            
            # Update trade in database
            trade.exit_ts = datetime.now()
            trade.exit_price = exit_price
            trade.pnl_usdt = pnl_usdt
            trade.pnl_pct = pnl_pct
            trade.reason_exit = reason
            
            self.db.commit()
            
            # Update risk manager
            self.risk_manager.record_trade_close(self.current_bar)
            
            # Send Telegram notification
            message = f"""
🔴 <b>Trade Closed</b>
📊 {trade.symbol}
💰 P&L: ${pnl_usdt:,.2f} ({pnl_pct:+.2f}%)
📈 Exit: ${exit_price:.2f}
🎯 Reason: {reason}
            """.strip()
            
            asyncio.create_task(self.tg_send(message))
            
            # Log alert
            self.alert_repo.insert_alert(
                'info' if pnl_usdt >= 0 else 'warn',
                f"Trade closed: {trade.symbol} ${pnl_usdt:,.2f} ({reason})"
            )
            
            logger.info(f"Trade closed: {trade.symbol} ${pnl_usdt:,.2f} ({reason})")
            
        except Exception as e:
            logger.error(f"Error closing trade: {e}")

    def should_enter_trade(self) -> bool:
        """Check if we should enter a new trade"""
        try:
            # Check if paused
            if self.is_paused():
                logger.info("Trading is paused")
                return False
            
            # Check if we have open trades for this symbol
            open_trades = self.get_open_trades()
            if any(t.symbol == self.symbol for t in open_trades):
                logger.info(f"Already have open trades for {self.symbol}")
                return False
            
            # Check risk manager
            can_trade = self.risk_manager.can_open_trade(self.current_bar)
            if not can_trade:
                logger.info("Risk manager prevents trading")
            return can_trade
            
        except Exception as e:
            logger.error(f"Error checking if should enter trade: {e}")
            return False

    async def process_signal(self, signal: Dict) -> None:
        """Process a trading signal"""
        try:
            if signal['signal'] != 'long':
                logger.info(f"Signal is not long: {signal['signal']}")
                return

            if not self.should_enter_trade():
                logger.info("Should not enter trade - checking conditions...")
                return

            symbol_info = self.exchange.get_symbol_info(self.symbol)
            lot_step = symbol_info.get('stepSize', 0.001)
            
            logger.info(f"Processing LONG signal - Entry: ${signal['entry_ref_price']:.2f}, SL: ${signal['sl']:.2f}, Lot Step: {lot_step}")

            qty = self.risk_manager.calculate_position_size(
                signal['entry_ref_price'],
                signal['sl'],
                lot_step
            )

            if qty <= 0:
                logger.warning(f"Position size is zero or negative: {qty}")
                return

            trade = self.trade_repo.open_trade(
                symbol=self.symbol,
                qty=qty,
                entry_price=signal['entry_ref_price'],
                sl=signal['sl'],
                tp1=signal['tp1'],
                trail_mult=0.02
            )

            self.risk_manager.increment_trades_today()
            message = f"""
🟢 <b>Trade Entry</b>
📊 {qty} {self.symbol}
💰 Price: ${signal['entry_ref_price']:.2f}
🛑 SL: ${signal['sl']:.2f}
🎯 TP1: ${signal['tp1']:.2f}
            """.strip()
            
            await self.tg_send(message)
            logger.info(f"Trade opened: {qty} {self.symbol} @ ${signal['entry_ref_price']:.2f}")

        except Exception as e:
            logger.error(f"Error processing signal: {e}")

    async def trading_loop(self) -> None:
        """Main trading loop"""
        logger.info("Starting trading loop...")
        self.is_running = True
        
        # Start scheduler
        self.scheduler.start()
        logger.info("Scheduler started")

        while self.is_running:
            try:
                df = self.exchange.get_klines(self.symbol, self.interval, limit=100)
                if df.empty:
                    logger.warning("No klines data received")
                    self.record_api_failure()
                    await asyncio.sleep(5)
                    continue

                # Record successful API call
                self.record_api_success()

                if self.detect_new_bar(df):
                    logger.info(f"New {self.interval} bar detected")
                    df_with_indicators = calculate_all_indicators(df)
                    signal = generate_signal(df_with_indicators)
                    await self.process_signal(signal)
                    self.manage_exits()
                    if self.current_bar % 4 == 0:  # Hourly update for 15m bars
                        self.update_equity()

                await asyncio.sleep(5)

            except KeyboardInterrupt:
                logger.info("Trading loop interrupted")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                self.record_api_failure()
                await asyncio.sleep(5)

        # Stop scheduler
        self.scheduler.shutdown()
        logger.info("Trading loop stopped")

    def stop(self) -> None:
        """Stop the trading bot"""
        self.is_running = False
        if hasattr(self, 'scheduler'):
            self.scheduler.shutdown()
        logger.info("Trading bot stop requested")

async def main():
    """Main entry point"""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.info(f"Starting SOL Spot Bot in {settings.MODE} mode")
        logger.info(f"Timezone: {settings.TZ}")
        bot = TradingBot()
        await bot.trading_loop()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
