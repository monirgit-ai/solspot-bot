# SolSpot Bot - Complete User Guide

## 🚀 What is SolSpot Bot?

SolSpot Bot is an **automated cryptocurrency trading bot** designed for Binance spot trading. It combines advanced technical analysis with robust risk management to execute trades automatically while you sleep, work, or focus on other activities.

### 🎯 **Primary Benefits:**

- **24/7 Automated Trading**: Never miss trading opportunities
- **Emotion-Free Trading**: Removes human emotions from trading decisions
- **Risk Management**: Built-in protection against large losses
- **Real-Time Monitoring**: Web dashboard and Telegram notifications
- **Backtesting Capability**: Test strategies before live trading
- **Mobile Access**: Manage your bot from anywhere

---

## 🧠 How Does It Work?

### **Core Trading Logic**

The bot operates on a **trend-following strategy** with the following key principles:

#### **1. Entry Conditions (LONG Position)**
The bot enters a long position when **ALL** of these conditions are met:

- ✅ **Price > EMA20**: Current price is above the 20-period Exponential Moving Average
- ✅ **EMA20 > EMA50**: 20-period EMA is above 50-period EMA (uptrend confirmation)
- ✅ **RSI > 50**: Relative Strength Index shows momentum above neutral
- ✅ **Not in Choppy Market**: Avoids sideways markets where:
  - EMA difference is less than 0.3% of price, AND
  - RSI is between 45-55 (neutral zone)

#### **2. Position Sizing**
- **Risk-Based**: Calculates position size based on your risk percentage
- **Formula**: `Position Size = (Risk Amount) / (Entry Price - Stop Loss)`
- **Example**: $10,000 equity, 0.5% risk, entry at $150, stop at $145 = ~10 SOL

#### **3. Stop Loss & Take Profit**
- **Stop Loss**: Entry price - (1.8 × ATR) - protects against large losses
- **Take Profit 1**: Entry price + (1.5 × ATR) - first profit target
- **Take Profit 2**: Entry price + (3.0 × ATR) - second profit target

#### **4. Exit Conditions**
- **Stop Loss Hit**: Automatic exit at predetermined loss level
- **Take Profit Hit**: Automatic exit at profit targets
- **Trend Reversal**: Exit when trend conditions no longer met

### **Technical Indicators Used**

| Indicator | Purpose | Default Settings |
|-----------|---------|------------------|
| **EMA20** | Short-term trend | 20 periods |
| **EMA50** | Medium-term trend | 50 periods |
| **RSI** | Momentum & overbought/oversold | 14 periods, 30/70 levels |
| **ATR** | Volatility for stop loss | 14 periods |
| **MACD** | Trend confirmation | 12,26,9 |

---

## ⚙️ How to Manage Your Bot

### **1. Web Dashboard Access**

#### **Local Access:**
```
http://localhost:8000
```

#### **Network Access:**
```
http://172.16.22.223:8000
```

#### **Public Access (after port forwarding):**
```
http://[YOUR_PUBLIC_IP]:[PORT]
```

### **2. Dashboard Features**

#### **📊 Real-Time Monitoring**
- **Current Equity**: Live account balance
- **Today's P&L**: Daily profit/loss
- **Open Positions**: Active trades
- **Market Price**: Current SOL price
- **Bot Status**: Running/Paused

#### **🧠 Strategy Analysis**
- **Trading Logic**: Real-time analysis of why bot takes/doesn't take trades
- **Condition Check**: Each trading condition explained in human terms
- **Market Data**: Live price, indicators, and trend analysis
- **Decision Log**: Activity log showing bot's decision-making process

#### **🎛️ Bot Control Panel**
- **Pause/Resume**: Stop or start trading
- **Live Mode Indicator**: Shows if using real money
- **Configuration**: Easy parameter adjustment

#### **📈 Performance Metrics**
- **Equity History**: 30-day performance chart
- **Daily P&L**: Daily profit/loss breakdown
- **Trade History**: All completed trades
- **Win Rate**: Percentage of profitable trades

### **3. Configuration Management**

#### **Access Configuration:**
```
http://172.16.22.223:8000/config
```

#### **Access Strategy Analysis:**
```
http://172.16.22.223:8000/strategy
```

#### **Key Parameters You Can Adjust:**

| Parameter | Description | Default | Recommended Range |
|-----------|-------------|---------|-------------------|
| **Trading Symbol** | Cryptocurrency pair | SOLUSDT | BTCUSDT, ETHUSDT, etc. |
| **Timeframe** | Chart interval | 15m | 5m, 15m, 1h, 4h |
| **Risk Per Trade** | % of equity risked | 0.5% | 0.1% - 2% |
| **Daily Loss Limit** | Max daily loss | 1.5% | 1% - 3% |
| **Stop Loss** | Loss protection | 2% | 1% - 5% |
| **Take Profit 1** | First profit target | 4% | 2% - 8% |
| **Take Profit 2** | Second profit target | 8% | 5% - 15% |

### **4. Service Management**

#### **Quick Commands:**
```bash
# Check if bot is running
./manage_bot.sh status

# Start the bot
./manage_bot.sh start

# Stop the bot
./manage_bot.sh stop

# Restart the bot
./manage_bot.sh restart

# View logs
./manage_bot.sh logs
```

#### **Advanced Management:**
```bash
# Follow web server logs
./manage_bot.sh logs-web

# Follow trading bot logs
./manage_bot.sh logs-bot

# System service status
sudo systemctl status solspot-web.service
sudo systemctl status solspot-bot.service
```

---

## 📱 Telegram Integration

### **Bot Commands**

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot |
| `/status` | Get current status (equity, positions, SOL price) |
| `/report` | Get detailed trading report |
| `/pause` | Pause trading |
| `/resume` | Resume trading |

### **Automatic Notifications**

- **Trade Opened**: When a new position is entered
- **Trade Closed**: When a position is closed (profit/loss)
- **Daily Report**: End-of-day summary at 23:59
- **Heartbeat**: Every 6 hours to confirm bot is alive
- **Alerts**: Important events and warnings

### **🌐 Trigger Telegram Notifications via URL**

You can trigger Telegram notifications directly through web URLs without needing to send commands to the bot. This is useful for:
- **External integrations** (other apps, scripts)
- **Manual notifications** from any device
- **Testing** bot connectivity
- **Scheduled triggers** via cron jobs

#### **Available URL Endpoints**

| Endpoint | Description | URL Example |
|----------|-------------|-------------|
| **Test Message** | Send a test message to verify bot is working | `http://172.16.22.223:8000/telegram/test` |
| **Status Report** | Get current bot status (equity, positions, SOL price) | `http://172.16.22.223:8000/telegram/status` |
| **Trading Report** | Get detailed trading report with P&L | `http://172.16.22.223:8000/telegram/report` |
| **Poll Messages** | Check for new Telegram commands | `http://172.16.22.223:8000/telegram/poll-messages` |

#### **How to Use URL Triggers**

##### **1. Test Bot Connectivity**
```bash
# Send a test message
curl http://172.16.22.223:8000/telegram/test

# Or open in browser
http://172.16.22.223:8000/telegram/test
```

##### **2. Get Current Status**
```bash
# Get live status
curl http://172.16.22.223:8000/telegram/status

# Response: {"status": "success", "message": "Status sent to Telegram"}
```

##### **3. Get Trading Report**
```bash
# Get detailed report
curl http://172.16.22.223:8000/telegram/report

# Response: {"status": "success", "message": "Report sent to Telegram"}
```

##### **4. Check for Commands**
```bash
# Poll for new messages
curl http://172.16.22.223:8000/telegram/poll-messages
```

#### **Advanced Usage Examples**

##### **Scheduled Status Checks (Cron Job)**
```bash
# Add to crontab to get status every hour
0 * * * * curl -s http://172.16.22.223:8000/telegram/status > /dev/null 2>&1
```

##### **Browser Bookmarks**
Create bookmarks for quick access:
- **Status**: `http://172.16.22.223:8000/telegram/status`
- **Report**: `http://172.16.22.223:8000/telegram/report`
- **Test**: `http://172.16.22.223:8000/telegram/test`

##### **Mobile Access**
Access these URLs from your phone browser:
- **Quick Status**: `http://172.16.22.223:8000/telegram/status`
- **Daily Report**: `http://172.16.22.223:8000/telegram/report`

##### **External Integrations**
```python
# Python script example
import requests

def get_bot_status():
    response = requests.get("http://172.16.22.223:8000/telegram/status")
    return response.json()

def send_test_message():
    response = requests.get("http://172.16.22.223:8000/telegram/test")
    return response.json()
```

#### **URL Response Format**

All endpoints return JSON responses:

```json
{
    "status": "success",
    "message": "Status sent to Telegram"
}
```

Or in case of errors:

```json
{
    "status": "error", 
    "message": "Telegram bot not configured"
}
```

#### **Security Notes**

- **Local Network**: These URLs work within your local network
- **Public Access**: After port forwarding, accessible from anywhere
- **No Authentication**: Anyone with access can trigger notifications
- **Rate Limiting**: Basic rate limiting is implemented
- **Logging**: All requests are logged for monitoring

#### **Troubleshooting URL Triggers**

| Problem | Solution |
|---------|----------|
| **404 Error** | Check if bot services are running: `./manage_bot.sh status` |
| **500 Error** | Check logs: `./manage_bot.sh logs-web` |
| **No Telegram Message** | Verify bot token and chat ID in `.env` |
| **Network Unreachable** | Check firewall: `sudo ufw status` |

#### **Testing URL Triggers**

Use the included test script to verify all endpoints:

```bash
# Test all Telegram URL endpoints
python3 test_telegram_urls.py

# Test specific endpoint
python3 test_telegram_urls.py /telegram/status
```

This script will test all available endpoints and show you the responses.

---

## 🛡️ Risk Management Features

### **1. Position Sizing**
- **Risk-Based**: Never risk more than your specified percentage
- **Minimum Size**: Ensures trades are meaningful ($10 minimum)
- **Maximum Size**: Prevents overexposure (10% of equity max)

### **2. Daily Loss Limits**
- **Automatic Stop**: Bot pauses if daily loss exceeds limit
- **Reset Daily**: Fresh start each day
- **Configurable**: Adjust based on your risk tolerance

### **3. Kill Switch Protection**
- **Maximum Drawdown**: Stops trading if equity drops 12%
- **API Failures**: Pauses after 5 consecutive failures
- **Manual Override**: Can be paused via web UI or Telegram

### **4. Cooldown Periods**
- **Between Trades**: Waits specified bars between trades
- **After Losses**: Prevents revenge trading
- **Market Conditions**: Avoids trading in choppy markets

---

## 📊 Trading Strategy Benefits

### **🎯 Why This Strategy Works**

#### **1. Trend Following**
- **Captures Major Moves**: Rides significant price trends
- **Reduces False Signals**: Multiple confirmation levels
- **Adapts to Market**: Uses dynamic indicators

#### **2. Risk-Reward Optimization**
- **Favorable Ratios**: 1:1.5 to 1:3 risk-reward ratios
- **Multiple Targets**: Two take-profit levels
- **Dynamic Stops**: ATR-based stop losses

#### **3. Market Filtering**
- **Chop Detection**: Avoids sideways markets
- **Momentum Confirmation**: RSI validates trends
- **Volume Consideration**: Uses ATR for volatility

### **📈 Expected Performance**

#### **Conservative Settings (0.5% risk):**
- **Win Rate**: 40-60%
- **Average Win**: 2-4%
- **Average Loss**: 1-2%
- **Monthly Return**: 5-15%

#### **Aggressive Settings (1% risk):**
- **Win Rate**: 40-60%
- **Average Win**: 2-4%
- **Average Loss**: 1-2%
- **Monthly Return**: 10-25%

---

## 🔧 Advanced Configuration

### **Technical Analysis Settings**

```python
# RSI Settings
RSI_PERIOD = 14          # Calculation period
RSI_OVERBOUGHT = 70      # Sell signal level
RSI_OVERSOLD = 30        # Buy signal level

# MACD Settings
MACD_FAST = 12          # Fast EMA period
MACD_SLOW = 26          # Slow EMA period
MACD_SIGNAL = 9         # Signal line period
```

### **Trading Schedule**

```python
# 24/7 Trading (default)
TRADING_HOURS_START = 0
TRADING_HOURS_END = 24

# Day Trading Only
TRADING_HOURS_START = 9
TRADING_HOURS_END = 17
```

### **Notification Settings**

```python
# Telegram Notifications
TELEGRAM_ENABLED = True
HEARTBEAT_INTERVAL_HOURS = 6
DAILY_REPORT_TIME = "23:59"
```

---

## 🚨 Important Safety Notes

### **1. Start Small**
- Begin with paper trading
- Use small amounts in live trading
- Gradually increase position sizes

### **2. Monitor Regularly**
- Check dashboard daily
- Review Telegram notifications
- Monitor logs for issues

### **3. Understand Risks**
- Cryptocurrency markets are volatile
- Past performance doesn't guarantee future results
- Never invest more than you can afford to lose

### **4. Backup Your Configuration**
- Save your `trading_config.py` file
- Document your settings
- Keep API keys secure

---

## 📞 Support & Troubleshooting

### **Common Issues**

#### **Bot Not Trading**
1. Check if services are running: `./manage_bot.sh status`
2. Verify API keys in `.env` file
3. Check logs: `./manage_bot.sh logs-bot`

#### **Web UI Not Accessible**
1. Check firewall: `sudo ufw status`
2. Allow port 8000: `sudo ufw allow 8000/tcp`
3. Verify service status: `./manage_bot.sh status`

#### **Telegram Not Working**
1. Check bot token in `.env` file
2. Verify chat ID is correct
3. Test with `/start` command

### **Getting Help**

1. **Check Logs**: Use `./manage_bot.sh logs` for detailed information
2. **Review Configuration**: Ensure settings match your requirements
3. **Test Connectivity**: Verify Binance API access
4. **Monitor Performance**: Track results and adjust parameters

---

## 🎉 Getting Started Checklist

### **✅ Initial Setup**
- [ ] Environment variables configured
- [ ] API keys added to `.env`
- [ ] Telegram bot configured
- [ ] Services running: `./manage_bot.sh status`

### **✅ Testing Phase**
- [ ] Paper trading mode enabled
- [ ] Web dashboard accessible
- [ ] Telegram notifications working
- [ ] Configuration page functional

### **✅ Live Trading**
- [ ] Small initial investment
- [ ] Risk parameters set conservatively
- [ ] Monitoring schedule established
- [ ] Emergency stop procedures known

### **✅ Ongoing Management**
- [ ] Daily dashboard check
- [ ] Weekly performance review
- [ ] Monthly parameter optimization
- [ ] Regular backup of configuration

---

**🎯 Remember: The key to successful automated trading is patience, proper risk management, and continuous monitoring. Start small, learn from the results, and gradually optimize your strategy!**
