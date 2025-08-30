from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from telegram import Update
from telegram.ext import Application
import json
import logging
import httpx
import time
import hmac
import hashlib
from .db import get_db
from .repo import SettingRepository, EquityRepository, TradeRepository, AlertRepository
from .config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def tg_send(text: str, chat_id: int = None) -> bool:
    """Send message to Telegram using httpx"""
    if not settings.TG_BOT_TOKEN:
        logger.error("Telegram bot token not configured")
        return False
    
    if not chat_id and not settings.TG_CHAT_ID:
        logger.error("No chat ID configured")
        return False
    
    target_chat_id = chat_id or settings.TG_CHAT_ID
    
    try:
        url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            response.raise_for_status()
            
        logger.info(f"Message sent to chat {target_chat_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Telegram webhook updates"""
    try:
        # Parse the incoming update
        body = await request.body()
        update_data = json.loads(body)
        update = Update.de_json(update_data, None)
        
        # Handle different types of updates
        if update.message:
            await handle_message(update.message, db)
        elif update.callback_query:
            await handle_callback_query(update.callback_query, db)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_message(message, db: Session):
    """Handle incoming Telegram messages"""
    # Handle commands
    if message.text and message.text.startswith('/'):
        await handle_command(message, db)
    else:
        # Handle regular messages
        await message.reply_text("I'm a trading bot. Use /help to see available commands.")


async def handle_command(message, db: Session):
    """Handle Telegram bot commands"""
    command = message.text.split()[0].lower()
    chat_id = message.chat.id
    
    if command == "/status":
        await handle_status_command(chat_id, db)
    
    elif command == "/pause":
        await handle_pause_command(chat_id, db)
    
    elif command == "/resume":
        await handle_resume_command(chat_id, db)
    
    elif command == "/report":
        await handle_report_command(chat_id, db)
    
    elif command == "/help":
        await handle_help_command(chat_id)
    
    else:
        await handle_unknown_command(chat_id)


async def handle_status_command(chat_id: int, db: Session):
    """Handle /status command"""
    try:
        setting_repo = SettingRepository(db)
        trade_repo = TradeRepository(db)
        
        # Get settings
        mode = setting_repo.get_setting('mode') or settings.MODE
        is_paused = setting_repo.get_setting('is_paused') == 'true'
        
        # Get real-time data from Binance if in LIVE mode
        if mode == 'live' and settings.BINANCE_API_KEY and settings.BINANCE_API_SECRET:
            try:
                # Get real account balance
                async with httpx.AsyncClient() as client:
                    # Get account info
                    timestamp = int(time.time() * 1000)
                    query_string = f"timestamp={timestamp}"
                    signature = hmac.new(
                        settings.BINANCE_API_SECRET.encode('utf-8'),
                        query_string.encode('utf-8'),
                        hashlib.sha256
                    ).hexdigest()
                    
                    url = f"https://api.binance.com/api/v3/account?{query_string}&signature={signature}"
                    headers = {"X-MBX-APIKEY": settings.BINANCE_API_KEY}
                    response = await client.get(url, headers=headers)
                    
                    if response.status_code == 200:
                        account_data = response.json()
                        balances = account_data.get('balances', [])
                        
                        # Find USDT balance
                        usdt_balance = 0
                        sol_balance = 0
                        for balance in balances:
                            if balance['asset'] == 'USDT':
                                usdt_balance = float(balance['free']) + float(balance['locked'])
                            elif balance['asset'] == 'SOL':
                                sol_balance = float(balance['free']) + float(balance['locked'])
                        
                        # Calculate total equity (USDT + SOL value)
                        sol_price = 0
                        try:
                            price_response = await client.get("https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT")
                            if price_response.status_code == 200:
                                price_data = price_response.json()
                                sol_price = float(price_data['price'])
                        except:
                            pass
                        
                        total_equity = usdt_balance + (sol_balance * sol_price)
                        equity_text = f"${total_equity:,.2f}"
                        sol_price_text = f"${sol_price:.2f}"
                        
                        # Get open positions from database
                        open_trades = trade_repo.get_open_trades()
                        open_pos_count = len(open_trades)
                        
                        # Format open positions details
                        open_positions_text = "None"
                        if open_trades:
                            positions = []
                            for trade in open_trades:
                                positions.append(f"{trade.symbol} @ ${trade.entry_price:.2f}")
                            open_positions_text = ", ".join(positions)
                        
                        # Calculate today's P&L (simplified - you might want to enhance this)
                        today_pnl = 0.0  # This would need more complex calculation
                        
                        status_text = f"""
🤖 <b>Bot Status (LIVE DATA)</b>

📊 <b>Mode:</b> {mode.upper()}
⏸️ <b>Paused:</b> {'Yes' if is_paused else 'No'}
💰 <b>Total Equity:</b> {equity_text}
💵 <b>USDT Balance:</b> ${usdt_balance:,.2f}
🪙 <b>SOL Balance:</b> {sol_balance:.4f}
📈 <b>Open Positions:</b> {open_pos_count}
📋 <b>Positions:</b> {open_positions_text}
💱 <b>SOL Price:</b> {sol_price_text}
                        """.strip()
                        
                    else:
                        # Fallback to database data
                        raise Exception("Failed to get account data")
                        
            except Exception as e:
                logger.error(f"Error getting live data: {e}")
                # Fallback to database data
                await handle_status_command_fallback(chat_id, db)
                return
        else:
            # Use database data for paper mode
            await handle_status_command_fallback(chat_id, db)
            return
        
        await tg_send(status_text, chat_id)
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await tg_send("❌ Error getting status", chat_id)


async def handle_status_command_fallback(chat_id: int, db: Session):
    """Fallback status command using database data"""
    try:
        import time
        import hmac
        import hashlib
        
        setting_repo = SettingRepository(db)
        equity_repo = EquityRepository(db)
        trade_repo = TradeRepository(db)
        
        # Get settings
        mode = setting_repo.get_setting('mode') or settings.MODE
        is_paused = setting_repo.get_setting('is_paused') == 'true'
        
        # Get equity from database
        latest_equity = equity_repo.latest_equity()
        equity = latest_equity.equity_usdt if latest_equity else 0
        
        # Get open positions
        open_trades = trade_repo.get_open_trades()
        open_pos_count = len(open_trades)
        
        # Get today's P&L
        today_metrics = equity_repo.today_metrics()
        today_pnl = today_metrics['daily_pnl']
        
        # Get current SOL price
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT")
                if response.status_code == 200:
                    price_data = response.json()
                    sol_price = float(price_data['price'])
                    sol_price_text = f"${sol_price:.2f}"
                else:
                    sol_price_text = "N/A"
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            sol_price_text = "N/A"
        
        # Format open positions details
        open_positions_text = "None"
        if open_trades:
            positions = []
            for trade in open_trades:
                positions.append(f"{trade.symbol} @ ${trade.entry_price:.2f}")
            open_positions_text = ", ".join(positions)
        
        status_text = f"""
🤖 <b>Bot Status (PAPER MODE)</b>

📊 <b>Mode:</b> {mode.upper()}
⏸️ <b>Paused:</b> {'Yes' if is_paused else 'No'}
💰 <b>Current Equity:</b> ${equity:,.2f}
📈 <b>Open Positions:</b> {open_pos_count}
📋 <b>Positions:</b> {open_positions_text}
📊 <b>Today P&L:</b> ${today_pnl:,.2f}
💱 <b>SOL Price:</b> {sol_price_text}
        """.strip()
        
        await tg_send(status_text, chat_id)
        
    except Exception as e:
        logger.error(f"Error in fallback status command: {e}")
        await tg_send("❌ Error getting status", chat_id)


async def handle_pause_command(chat_id: int, db: Session):
    """Handle /pause command"""
    try:
        setting_repo = SettingRepository(db)
        setting_repo.set_setting('is_paused', 'true')
        
        await tg_send("⏸️ Bot paused", chat_id)
        
        # Log alert
        alert_repo = AlertRepository(db)
        alert_repo.insert_alert('info', 'Bot paused via Telegram command')
        
    except Exception as e:
        logger.error(f"Error in pause command: {e}")
        await tg_send("❌ Error pausing bot", chat_id)


async def handle_resume_command(chat_id: int, db: Session):
    """Handle /resume command"""
    try:
        setting_repo = SettingRepository(db)
        setting_repo.set_setting('is_paused', 'false')
        
        await tg_send("▶️ Bot resumed", chat_id)
        
        # Log alert
        alert_repo = AlertRepository(db)
        alert_repo.insert_alert('info', 'Bot resumed via Telegram command')
        
    except Exception as e:
        logger.error(f"Error in resume command: {e}")
        await tg_send("❌ Error resuming bot", chat_id)


async def handle_report_command(chat_id: int, db: Session):
    """Handle /report command"""
    try:
        trade_repo = TradeRepository(db)
        equity_repo = EquityRepository(db)
        
        # Get trade summary
        trade_summary = trade_repo.get_trade_summary()
        
        # Get today's metrics
        today_metrics = equity_repo.today_metrics()
        
        report_text = f"""
📊 <b>Trading Report</b>

📈 <b>Total Trades:</b> {trade_summary['total_trades']}
🔄 <b>Open Trades:</b> {trade_summary['open_trades']}
✅ <b>Closed Trades:</b> {trade_summary['closed_trades']}
🏆 <b>Win Rate:</b> {trade_summary['win_rate']:.1f}%
💰 <b>Total P&L:</b> ${trade_summary['total_pnl']:,.2f}
📊 <b>Today P&L:</b> ${today_metrics['daily_pnl']:,.2f}
        """.strip()
        
        await tg_send(report_text, chat_id)
        
    except Exception as e:
        logger.error(f"Error in report command: {e}")
        await tg_send("❌ Error generating report", chat_id)


async def handle_help_command(chat_id: int):
    """Handle /help command"""
    help_text = """
🤖 <b>SolSpot Bot Commands</b>

/status - Show bot status, mode, equity, open positions, today P&L
/pause - Pause the bot
/resume - Resume the bot
/report - Show trading report with win rate and P&L
/help - Show this help message
    """.strip()
    
    await tg_send(help_text, chat_id)


async def handle_unknown_command(chat_id: int):
    """Handle unknown commands"""
    await handle_help_command(chat_id)


async def handle_callback_query(callback_query, db: Session):
    """Handle callback queries from inline keyboards"""
    await callback_query.answer()
    
    # Handle different callback data
    if callback_query.data == "status":
        await handle_status_command(callback_query.message.chat.id, db)
    elif callback_query.data == "report":
        await handle_report_command(callback_query.message.chat.id, db)
    else:
        await callback_query.message.edit_text("Unknown callback")


@router.get("/test")
async def test_telegram():
    """Test Telegram bot by sending a test message"""
    if not settings.TG_BOT_TOKEN or not settings.TG_CHAT_ID:
        raise HTTPException(status_code=400, detail="Telegram bot not configured")
    
    try:
        success = await tg_send("🧪 Test message from SolSpot Bot")
        if success:
            return {"status": "success", "message": "Test message sent"}
        else:
            return {"status": "error", "message": "Failed to send test message"}
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to send test message")


@router.get("/set-webhook")
async def set_webhook():
    """Set up Telegram webhook (for manual setup)"""
    if not settings.TG_BOT_TOKEN:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")
    
    try:
        # For HTTP servers, we'll use polling instead of webhook
        # First, delete any existing webhook
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/deleteWebhook"
            response = await client.post(url)
            
            if response.status_code == 200:
                return {"status": "success", "message": "Webhook deleted. Use /poll-messages to check for commands."}
            else:
                return {"status": "error", "message": f"HTTP error: {response.status_code}"}
                
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set webhook: {str(e)}")


@router.get("/poll-messages")
async def poll_messages():
    """Poll for new messages (alternative to webhook)"""
    if not settings.TG_BOT_TOKEN:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            url = f"https://api.telegram.org/bot{settings.TG_BOT_TOKEN}/getUpdates"
            response = await client.get(url)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok') and result.get('result'):
                    updates = result['result']
                    # Process the latest update
                    if updates:
                        latest_update = updates[-1]
                        if 'message' in latest_update and 'text' in latest_update['message']:
                            message_text = latest_update['message']['text']
                            chat_id = latest_update['message']['chat']['id']
                            
                            # Handle commands
                            if message_text.startswith('/'):
                                await handle_command_poll(message_text, chat_id)
                                return {"status": "success", "message": f"Processed command: {message_text}"}
                    
                    return {"status": "success", "message": f"Found {len(updates)} updates"}
                else:
                    return {"status": "success", "message": "No new messages"}
            else:
                return {"status": "error", "message": f"HTTP error: {response.status_code}"}
                
    except Exception as e:
        logger.error(f"Error polling messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to poll messages: {str(e)}")


@router.get("/status")
async def get_status():
    """Get bot status directly via web endpoint"""
    if not settings.TG_BOT_TOKEN or not settings.TG_CHAT_ID:
        raise HTTPException(status_code=400, detail="Telegram bot not configured")
    
    try:
        # Import here to avoid circular imports
        from .db import get_db
        from sqlalchemy.orm import Session
        
        # Create a database session
        db = next(get_db())
        
        # Send status to Telegram
        await handle_status_command(int(settings.TG_CHAT_ID), db)
        
        return {"status": "success", "message": "Status sent to Telegram"}
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send status: {str(e)}")


@router.get("/report")
async def get_report():
    """Get trading report directly via web endpoint"""
    if not settings.TG_BOT_TOKEN or not settings.TG_CHAT_ID:
        raise HTTPException(status_code=400, detail="Telegram bot not configured")
    
    try:
        # Import here to avoid circular imports
        from .db import get_db
        from sqlalchemy.orm import Session
        
        # Create a database session
        db = next(get_db())
        
        # Send report to Telegram
        await handle_report_command(int(settings.TG_CHAT_ID), db)
        
        return {"status": "success", "message": "Report sent to Telegram"}
        
    except Exception as e:
        logger.error(f"Error in report endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send report: {str(e)}")


async def handle_command_poll(command: str, chat_id: int):
    """Handle commands from polling"""
    try:
        # Import here to avoid circular imports
        from .db import get_db
        from sqlalchemy.orm import Session
        
        # Create a database session
        db = next(get_db())
        
        if command.startswith('/status'):
            await handle_status_command(chat_id, db)
        elif command.startswith('/help'):
            await handle_help_command(chat_id)
        elif command.startswith('/report'):
            await handle_report_command(chat_id, db)
        else:
            await handle_help_command(chat_id)
            
    except Exception as e:
        logger.error(f"Error handling command: {e}")
        await tg_send("❌ Error processing command", chat_id)
