#!/bin/bash
# Script: render_keep_alive.sh
# Purpose: Ping Render Web Service every 5 minutes to prevent Free Tier from sleeping
# Target: https://moc-phet-linebot.onrender.com/health

LOG_FILE="/home/pohlor27/pstack-antigravity-main/line_daily_bot/keep_alive.log"
URL="https://moc-phet-linebot.onrender.com/health"

RESPONSE=$(curl -s -m 15 -w " | HTTP: %{http_code} | Time: %{time_total}s" "$URL")
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Keep-Alive Ping -> $RESPONSE" >> "$LOG_FILE"

# Keep log file under 500 lines to prevent unbounded growth
if [ -f "$LOG_FILE" ] && [ $(wc -l < "$LOG_FILE") -gt 500 ]; then
    tail -n 300 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
