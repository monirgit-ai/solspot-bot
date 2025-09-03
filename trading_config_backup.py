# Trading Configuration
# Edit these values to customize your trading bot

# Trading Symbol and Timeframe
TRADING_SYMBOL = "SOLUSDT"  # Change to: BTCUSDT, ETHUSDT, ADAUSDT, etc.
TIMEFRAME = "15m"  # Change to: 1m, 5m, 15m, 30m, 1h, 4h, 1d

# Risk Management
INITIAL_EQUITY = 100.0  # Starting equity in USDT
RISK_PER_TRADE_PCT = 0.01  # 1% risk per trade (0.01 = 1%)
DAILY_LOSS_STOP_PCT = 0.05  # 5% daily loss limit (0.01 = 1%)
COOLDOWN_BARS = 1  # Bars to wait between trades

# Position Sizing
MAX_POSITION_SIZE_PCT = 0.2  # Maximum 20% of equity per trade
MIN_POSITION_SIZE_USDT = 1.0  # Minimum $1 per trade

# Stop Loss and Take Profit
STOP_LOSS_PCT = 0.02  # 2% stop loss (0.01 = 1%)
TAKE_PROFIT_1_PCT = 0.04  # 4% take profit 1 (0.01 = 1%)
TAKE_PROFIT_2_PCT = 0.08  # 8% take profit 2 (0.01 = 1%)

# Trading Schedule
TRADING_HOURS_START = 0  # 24-hour format (0 = midnight)
TRADING_HOURS_END = 24  # 24-hour format (24 = midnight)

# Technical Analysis
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Notifications
TELEGRAM_ENABLED = True
HEARTBEAT_INTERVAL_HOURS = 6
DAILY_REPORT_TIME = "23:59"  # HH:MM format

# Kill Switch Settings
MAX_DRAWDOWN_PCT = 12.0  # 12% maximum drawdown
MAX_API_FAILURES = 5  # Pause after 5 consecutive API failures
