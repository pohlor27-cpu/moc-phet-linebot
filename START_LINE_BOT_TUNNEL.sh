#!/bin/bash
# สคริปต์เปิด Cloudflare Tunnel สำหรับ LINE Bot Webhook (Moc-bot)
echo "================================================================="
echo "   🤖 LINE Bot Webhook Tunnel (Cloudflare HTTPS)"
echo "   สำนักงานพาณิชย์จังหวัดเพชรบุรี"
echo "   พอร์ตบริการ: 8080 (URL: https://.../callback)"
echo "================================================================="

cloudflared tunnel --protocol http2 --url http://localhost:8080
