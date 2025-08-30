# SolSpot Bot 🤖

A production-ready automated cryptocurrency trading bot for Binance spot trading with advanced technical analysis, risk management, and real-time monitoring.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🌟 Features

- **🤖 Automated Trading**: 24/7 cryptocurrency trading on Binance
- **📊 Technical Analysis**: EMA, RSI, MACD, ATR indicators
- **🛡️ Risk Management**: Position sizing, stop-loss, daily limits
- **📱 Web Dashboard**: Real-time monitoring and control
- **📲 Telegram Integration**: Notifications and remote control
- **📈 Strategy Analysis**: Live trading logic explanation
- **🔄 System Services**: Persistent background operation
- **📱 Mobile Responsive**: Works on all devices

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Binance API account
- Telegram Bot (optional)
- Ubuntu/Debian server (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/solspot-bot.git
   cd solspot-bot
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys and settings
   ```

4. **Run the bot**
   ```bash
   # Start web server
   uvicorn api.app.main:app --host 0.0.0.0 --port 8000
   
   # Start trading bot (in another terminal)
   python -m strategy.main
   ```

## 📖 Documentation

- **[User Guide](USER_GUIDE.md)** - Complete user manual
- **[Quick Reference](QUICK_REFERENCE.md)** - Essential commands
- **[Service Management](SERVICE_MANAGEMENT.md)** - System service setup

## 🏗️ Project Structure

```
solspot-bot/
├── api/                    # FastAPI web application
│   └── app/
│       ├── routes/         # API endpoints
│       ├── templates/      # HTML templates
│       ├── static/         # CSS, JS, images
│       ├── main.py         # FastAPI app entry point
│       ├── config.py       # Configuration management
│       ├── db.py           # Database setup
│       ├── models.py       # SQLAlchemy models
│       ├── repo.py         # Repository pattern
│       └── telegram_webhook.py  # Telegram integration
├── strategy/               # Trading strategy logic
│   ├── main.py            # Main trading loop
│   ├── exchange.py        # Binance API wrapper
│   ├── indicators.py      # Technical indicators
│   ├── signal.py          # Signal generation
│   └── risk.py            # Risk management
├── common/                 # Shared utilities
├── requirements.txt        # Python dependencies
├── env.example            # Environment variables template
├── trading_config.py      # Trading parameters
├── manage_bot.sh          # Service management script
└── README.md              # This file
```

## 🎯 Trading Strategy

### Entry Conditions (ALL must be true)
- ✅ **Price > EMA20**: Uptrend confirmation
- ✅ **EMA20 > EMA50**: Trend alignment
- ✅ **RSI > 50**: Momentum positive
- ✅ **Not in Choppy Market**: Clear trend direction

### Risk Management
- **Position Sizing**: Risk-based calculation (0.5% per trade)
- **Stop Loss**: ATR-based dynamic stops
- **Take Profit**: Multiple profit targets
- **Daily Limits**: Maximum daily loss protection
- **Kill Switch**: Maximum drawdown protection

## 🌐 Web Interface

### Access URLs
- **Dashboard**: `http://your-server:8000`
- **Strategy Analysis**: `http://your-server:8000/strategy`
- **Configuration**: `http://your-server:8000/config`

### Features
- **Real-time Monitoring**: Live equity, P&L, positions
- **Strategy Analysis**: Trading logic explanation
- **Configuration Management**: Easy parameter adjustment
- **Bot Control**: Pause/resume functionality
- **Mobile Responsive**: Works on all devices

## 📱 Telegram Integration

### Bot Commands
- `/start` - Initialize bot
- `/status` - Get current status
- `/report` - Get trading report
- `/pause` - Pause trading
- `/resume` - Resume trading

### URL Triggers
- **Test**: `http://your-server:8000/telegram/test`
- **Status**: `http://your-server:8000/telegram/status`
- **Report**: `http://your-server:8000/telegram/report`

## 🔧 Configuration

### Trading Parameters
```python
# trading_config.py
TRADING_SYMBOL = "SOLUSDT"      # Trading pair
TIMEFRAME = "15m"               # Chart interval
RISK_PER_TRADE_PCT = 0.005      # 0.5% risk per trade
DAILY_LOSS_STOP_PCT = 0.015     # 1.5% daily limit
STOP_LOSS_PCT = 0.02            # 2% stop loss
TAKE_PROFIT_1_PCT = 0.04        # 4% take profit 1
TAKE_PROFIT_2_PCT = 0.08        # 8% take profit 2
```

### Environment Variables
```bash
# .env
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
TG_BOT_TOKEN=your_telegram_bot_token
TG_CHAT_ID=your_chat_id
MODE=paper  # or live
```

## 🚀 Production Deployment

### System Services Setup
```bash
# Copy service files
sudo cp solspot-web.service /etc/systemd/system/
sudo cp solspot-bot.service /etc/systemd/system/

# Enable and start services
sudo systemctl enable solspot-web.service
sudo systemctl enable solspot-bot.service
sudo systemctl start solspot-web.service
sudo systemctl start solspot-bot.service
```

### Management Commands
```bash
# Check status
./manage_bot.sh status

# Start/stop services
./manage_bot.sh start
./manage_bot.sh stop

# View logs
./manage_bot.sh logs
```

## 📊 Performance

### Expected Results
- **Win Rate**: 40-60%
- **Risk-Reward**: 1:1.5 to 1:3
- **Monthly Return**: 5-25% (depending on risk settings)

### Risk Disclaimer
⚠️ **Cryptocurrency trading involves substantial risk. Past performance does not guarantee future results. Never invest more than you can afford to lose.**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [User Guide](USER_GUIDE.md)
- **Issues**: Report bugs on [GitHub Issues](https://github.com/yourusername/solspot-bot/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/yourusername/solspot-bot/discussions)

## 🙏 Acknowledgments

- [Binance API](https://binance-docs.github.io/apidocs/) for trading data
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [TA-Lib](https://ta-lib.org/) for technical indicators
- [Bootstrap](https://getbootstrap.com/) for the UI framework

---

**⭐ If you find this project helpful, please give it a star!**
