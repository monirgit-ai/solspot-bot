# Improved Trading Configuration
# Based on analysis of last 3 trades and market conditions

# Trading Symbol and Timeframe
TRADING_SYMBOL = "SOLUSDT"
TIMEFRAME = "15m"

# ===== RISK MANAGEMENT IMPROVEMENTS =====
INITIAL_EQUITY = 100.0
RISK_PER_TRADE_PCT = 0.008  # Reduced from 0.01 (1%) to 0.8%
DAILY_LOSS_STOP_PCT = 0.03  # Reduced from 0.05 (5%) to 3%
COOLDOWN_BARS = 2  # Increased from 1 to 2 bars

# NEW: Consecutive Loss Protection
MAX_CONSECUTIVE_LOSSES = 3  # Stop trading after 3 consecutive losses
CONSECUTIVE_LOSS_COOLDOWN_HOURS = 24  # Wait 24 hours after consecutive losses

# ===== STOP LOSS IMPROVEMENTS =====
STOP_LOSS_ATR_MULTIPLIER = 2.2  # Increased from 1.8 to 2.2
MIN_STOP_LOSS_PCT = 0.008  # Minimum 0.8% stop loss distance
MAX_STOP_LOSS_PCT = 0.025  # Maximum 2.5% stop loss distance

# ===== SIGNAL ENHANCEMENTS =====
MIN_TREND_STRENGTH = 0.005  # Minimum EMA difference (0.5%)
MAX_RSI_ENTRY = 70  # Maximum RSI for entry (avoid overbought)
MIN_RSI_ENTRY = 30  # Minimum RSI for entry (avoid oversold)

# NEW: Volume Confirmation
REQUIRE_VOLUME_CONFIRMATION = True
MIN_VOLUME_SMA_PERIOD = 20
MIN_VOLUME_RATIO = 0.8  # Current volume must be 80% of average

# NEW: Volatility Filters
MIN_ATR_PCT = 0.003  # Minimum ATR percentage (0.3%)
MAX_ATR_PCT = 0.015  # Maximum ATR percentage (1.5%)

# ===== POSITION SIZING IMPROVEMENTS =====
MAX_POSITION_SIZE_PCT = 0.15  # Reduced from 0.2 to 0.15
MIN_POSITION_SIZE_USDT = 1.0

# NEW: Dynamic Position Sizing
ENABLE_DYNAMIC_SIZING = True
SIGNAL_STRENGTH_MULTIPLIER = True  # Adjust size based on signal strength
RECENT_PERFORMANCE_MULTIPLIER = True  # Adjust size based on recent performance

# ===== TAKE PROFIT IMPROVEMENTS =====
TAKE_PROFIT_1_PCT = 0.03  # Reduced from 0.04 to 0.03 (3%)
TAKE_PROFIT_2_PCT = 0.06  # Reduced from 0.08 to 0.06 (6%)

# NEW: Trailing Stop
ENABLE_TRAILING_STOP = True
TRAILING_STOP_ACTIVATION_PCT = 0.015  # Activate at 1.5% profit
TRAILING_STOP_DISTANCE_PCT = 0.008  # Trail at 0.8% distance

# ===== MARKET CONDITION FILTERS =====
ENABLE_MARKET_FILTERS = True
AVOID_HIGH_VOLATILITY = True
AVOID_LOW_VOLUME = True
AVOID_WEEKEND_GAPS = True

# ===== TRADING SCHEDULE =====
TRADING_HOURS_START = 0
TRADING_HOURS_END = 24

# NEW: Avoid trading during major news events
AVOID_NEWS_EVENTS = True
NEWS_EVENT_BUFFER_MINUTES = 30

# ===== TECHNICAL ANALYSIS =====
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# NEW: Additional Indicators
BOLLINGER_BANDS_PERIOD = 20
BOLLINGER_BANDS_STD = 2
STOCHASTIC_K_PERIOD = 14
STOCHASTIC_D_PERIOD = 3

# ===== NOTIFICATIONS =====
TELEGRAM_ENABLED = True
HEARTBEAT_INTERVAL_HOURS = 6
DAILY_REPORT_TIME = "23:59"

# NEW: Enhanced Alerts
ALERT_ON_CONSECUTIVE_LOSSES = True
ALERT_ON_HIGH_DRAWDOWN = True
ALERT_ON_SIGNAL_QUALITY = True

# ===== KILL SWITCH SETTINGS =====
MAX_DRAWDOWN_PCT = 8.0  # Reduced from 12% to 8%
MAX_API_FAILURES = 5

# NEW: Performance-based Kill Switch
MIN_WIN_RATE = 0.4  # Minimum 40% win rate over last 20 trades
MAX_AVERAGE_LOSS = 0.015  # Maximum 1.5% average loss
PERFORMANCE_CHECK_PERIOD = 20  # Check every 20 trades

# ===== BACKTESTING AND OPTIMIZATION =====
ENABLE_BACKTESTING = True
BACKTEST_PERIOD_DAYS = 30
OPTIMIZATION_ENABLED = False  # Disable for live trading

# ===== DEBUGGING AND LOGGING =====
DEBUG_MODE = False
LOG_SIGNAL_DETAILS = True
LOG_MARKET_CONDITIONS = True
LOG_POSITION_SIZING = True

# ===== EMERGENCY SETTINGS =====
EMERGENCY_STOP_ON_LARGE_LOSS = True
LARGE_LOSS_THRESHOLD_PCT = 0.05  # 5% single trade loss
EMERGENCY_STOP_DURATION_HOURS = 6
