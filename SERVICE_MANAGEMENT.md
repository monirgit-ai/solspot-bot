# SolSpot Bot Service Management

## ✅ Services Now Running as System Services

The SolSpot Bot is now configured as **systemd services** that will:
- ✅ **Start automatically** when the server boots
- ✅ **Continue running** even after closing Cursor or terminal
- ✅ **Restart automatically** if they crash
- ✅ **Be accessible** from public IP after port forwarding

## 🚀 Quick Management Commands

Use the management script for easy control:

```bash
# Check status of both services
./manage_bot.sh status

# Start both services
./manage_bot.sh start

# Stop both services  
./manage_bot.sh stop

# Restart both services
./manage_bot.sh restart

# View recent logs
./manage_bot.sh logs

# Follow web server logs in real-time
./manage_bot.sh logs-web

# Follow trading bot logs in real-time
./manage_bot.sh logs-bot
```

## 🔧 Manual Systemctl Commands

If you prefer using systemctl directly:

```bash
# Check status
sudo systemctl status solspot-web.service
sudo systemctl status solspot-bot.service

# Start services
sudo systemctl start solspot-web.service
sudo systemctl start solspot-bot.service

# Stop services
sudo systemctl stop solspot-web.service
sudo systemctl stop solspot-bot.service

# Restart services
sudo systemctl restart solspot-web.service
sudo systemctl restart solspot-bot.service

# View logs
sudo journalctl -u solspot-web.service -f
sudo journalctl -u solspot-bot.service -f
```

## 🌐 Access URLs

- **Local Access**: http://localhost:8000
- **Network Access**: http://172.16.22.223:8000
- **Public Access**: http://[YOUR_PUBLIC_IP]:[PUBLIC_PORT] (after port forwarding)

## 🔄 Auto-Start on Boot

The services are configured to start automatically when the server boots. To verify:

```bash
sudo systemctl is-enabled solspot-web.service
sudo systemctl is-enabled solspot-bot.service
```

Both should return "enabled".

## 📊 Monitoring

### Check if services are running:
```bash
./manage_bot.sh status
```

### Monitor logs in real-time:
```bash
# Web server logs
./manage_bot.sh logs-web

# Trading bot logs  
./manage_bot.sh logs-bot
```

### Test web access:
```bash
curl http://172.16.22.223:8000/public-info
```

## 🛠️ Troubleshooting

### If services fail to start:
1. Check logs: `./manage_bot.sh logs`
2. Verify environment: Make sure `.env` file exists and has correct values
3. Check permissions: Ensure the `monir` user has access to the project directory

### If web UI is not accessible:
1. Check firewall: `sudo ufw status`
2. Allow port 8000: `sudo ufw allow 8000/tcp`
3. Check service status: `./manage_bot.sh status`

### If trading bot is not working:
1. Check API keys in `.env` file
2. Verify Binance API connectivity
3. Check logs: `./manage_bot.sh logs-bot`

## 🔒 Security Notes

- Services run under the `monir` user account
- Web server is accessible on all interfaces (0.0.0.0:8000)
- Consider setting up HTTPS for public access
- Monitor logs regularly for any issues

## 📝 Service Files Location

- **Web Service**: `/etc/systemd/system/solspot-web.service`
- **Bot Service**: `/etc/systemd/system/solspot-bot.service`
- **Management Script**: `/home/monir/solspot-bot/manage_bot.sh`

---

**✅ Your SolSpot Bot is now running as a persistent system service!**
It will continue running even after you close Cursor or restart the server.
