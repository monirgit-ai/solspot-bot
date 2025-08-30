#!/bin/bash

# SolSpot Bot Management Script
# Usage: ./manage_bot.sh [start|stop|restart|status|logs|logs-web|logs-bot]

case "$1" in
    start)
        echo "Starting SolSpot Bot services..."
        sudo systemctl start solspot-web.service
        sudo systemctl start solspot-bot.service
        echo "Services started!"
        ;;
    stop)
        echo "Stopping SolSpot Bot services..."
        sudo systemctl stop solspot-web.service
        sudo systemctl stop solspot-bot.service
        echo "Services stopped!"
        ;;
    restart)
        echo "Restarting SolSpot Bot services..."
        sudo systemctl restart solspot-web.service
        sudo systemctl restart solspot-bot.service
        echo "Services restarted!"
        ;;
    status)
        echo "=== SolSpot Web Server Status ==="
        sudo systemctl status solspot-web.service --no-pager
        echo ""
        echo "=== SolSpot Trading Bot Status ==="
        sudo systemctl status solspot-bot.service --no-pager
        ;;
    logs)
        echo "=== Recent logs from both services ==="
        echo "Web Server Logs:"
        sudo journalctl -u solspot-web.service -n 10 --no-pager
        echo ""
        echo "Trading Bot Logs:"
        sudo journalctl -u solspot-bot.service -n 10 --no-pager
        ;;
    logs-web)
        echo "=== Web Server Logs ==="
        sudo journalctl -u solspot-web.service -f
        ;;
    logs-bot)
        echo "=== Trading Bot Logs ==="
        sudo journalctl -u solspot-bot.service -f
        ;;
    *)
        echo "SolSpot Bot Management Script"
        echo ""
        echo "Usage: $0 [start|stop|restart|status|logs|logs-web|logs-bot]"
        echo ""
        echo "Commands:"
        echo "  start     - Start both services"
        echo "  stop      - Stop both services"
        echo "  restart   - Restart both services"
        echo "  status    - Show status of both services"
        echo "  logs      - Show recent logs from both services"
        echo "  logs-web  - Follow web server logs"
        echo "  logs-bot  - Follow trading bot logs"
        echo ""
        echo "Access URLs:"
        echo "  Local:     http://localhost:8000"
        echo "  Network:   http://172.16.22.223:8000"
        echo "  Public:    http://[PUBLIC_IP]:[PORT] (after port forwarding)"
        ;;
esac
