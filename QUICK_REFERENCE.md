# SolSpot Bot - Quick Reference Card

## 🚀 Essential Commands

### **Service Management**
```bash
# Check status
./manage_bot.sh status

# Start bot
./manage_bot.sh start

# Stop bot
./manage_bot.sh stop

# Restart bot
./manage_bot.sh restart

# View logs
./manage_bot.sh logs
```

### **Access URLs**
- **Dashboard**: http://172.16.22.223:8000
- **Strategy**: http://172.16.22.223:8000/strategy
- **Configuration**: http://172.16.22.223:8000/config
- **API Status**: http://172.16.22.223:8000/public-info

### **Telegram URL Triggers**
- **Test Message**: http://172.16.22.223:8000/telegram/test
- **Get Status**: http://172.16.22.223:8000/telegram/status
- **Get Report**: http://172.16.22.223:8000/telegram/report

## 📱 Telegram Commands

| Command | Action |
|---------|--------|
| `/start` | Initialize bot |
| `/status` | Get current status |
| `/report` | Get trading report |
| `/pause` | Pause trading |
| `/resume` | Resume trading |

### **🌐 URL Triggers (Alternative to Commands)**

| URL | Action |
|-----|--------|
| `http://172.16.22.223:8000/telegram/test` | Send test message |
| `http://172.16.22.223:8000/telegram/status` | Get current status |
| `http://172.16.22.223:8000/telegram/report` | Get trading report |

## ⚙️ Key Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Trading Symbol** | SOLUSDT | Cryptocurrency pair |
| **Timeframe** | 15m | Chart interval |
| **Risk Per Trade** | 0.5% | Risk percentage |
| **Daily Loss Limit** | 1.5% | Max daily loss |
| **Stop Loss** | 2% | Loss protection |
| **Take Profit 1** | 4% | First target |
| **Take Profit 2** | 8% | Second target |

## 🧠 Trading Logic Summary

### **Entry Conditions (ALL must be true)**
- ✅ Price > EMA20
- ✅ EMA20 > EMA50  
- ✅ RSI > 50
- ✅ Not in choppy market

### **Exit Conditions**
- 🛑 Stop Loss hit
- 🎯 Take Profit hit
- 📉 Trend reversal

## 🛡️ Risk Management

- **Position Sizing**: Risk-based calculation
- **Daily Limits**: Automatic stop at 1.5% loss
- **Kill Switch**: Stops at 12% drawdown
- **Cooldown**: 1 bar between trades

## 📊 Expected Performance

- **Win Rate**: 40-60%
- **Risk-Reward**: 1:1.5 to 1:3
- **Monthly Return**: 5-25% (depending on risk)

## 🚨 Emergency Procedures

### **Stop Trading Immediately**
```bash
./manage_bot.sh stop
```

### **Check What's Wrong**
```bash
./manage_bot.sh logs
```

### **Restart Services**
```bash
./manage_bot.sh restart
```

## 📞 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| **Bot not trading** | Check logs: `./manage_bot.sh logs-bot` |
| **Web UI not loading** | Check status: `./manage_bot.sh status` |
| **Telegram not working** | Verify bot token in `.env` |
| **API errors** | Check Binance API keys |

## 🎯 Best Practices

1. **Start Small**: Begin with paper trading
2. **Monitor Daily**: Check dashboard regularly
3. **Set Conservative Risk**: 0.5% risk per trade
4. **Keep Logs**: Monitor for issues
5. **Backup Config**: Save your settings

---

**📖 For detailed information, see: `USER_GUIDE.md`**
