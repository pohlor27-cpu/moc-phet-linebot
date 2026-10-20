#!/usr/bin/env python3
"""
Keep-Alive Daemon for Render Free Tier
Pings https://moc-phet-linebot.onrender.com/health every 5 minutes (300 seconds)
to keep the server awake 24/7 so daily notifications and scheduled tasks run reliably.
"""

import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

URL = "https://moc-phet-linebot.onrender.com/health"
LOG_FILE = Path(__file__).parent / "keep_alive.log"
INTERVAL_SECONDS = 300  # 5 minutes

def log_message(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {msg}\n"
    print(log_entry, end="")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to log: {e}")

def trim_log_if_needed():
    try:
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
            if len(lines) > 500:
                LOG_FILE.write_text("\n".join(lines[-300:]) + "\n", encoding="utf-8")
    except Exception:
        pass

def ping_render():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "MocPhetKeepAliveBot/1.0"}
    )
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            elapsed = time.time() - start_time
            log_message(f"Keep-Alive Ping -> HTTP {resp.getcode()} | Time: {elapsed:.2f}s | Status: ONLINE")
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start_time
        log_message(f"Keep-Alive Ping -> HTTP {e.code} | Time: {elapsed:.2f}s | Warn: {e.reason}")
    except Exception as e:
        elapsed = time.time() - start_time
        log_message(f"Keep-Alive Ping Error -> Time: {elapsed:.2f}s | {e}")

def main():
    log_message("🚀 Starting Render Keep-Alive Daemon (5-minute interval)...")
    while True:
        ping_render()
        trim_log_if_needed()
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
