#!/bin/bash
# สคริปต์รันและดูแลระบบ LINE OA Bot (Moc-bot) ประจำสำนักงานพาณิชย์จังหวัดเพชรบุรี

APP_DIR="/home/pohlor27/pstack-antigravity-main/line_daily_bot"
cd "$APP_DIR" || exit 1

LOG_FILE="$APP_DIR/line_bot.log"
PID_FILE="$APP_DIR/line_bot.pid"

case "$1" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "⚠️  LINE Bot กำลังทำงานอยู่แล้ว (PID: $(cat "$PID_FILE"))"
            exit 0
        fi
        echo "🚀 กำลังเริ่มระบบ LINE Bot (พอร์ต 8080)..."
        nohup python3 -u app.py > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        sleep 2
        if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "✅ LINE Bot ทำงานเรียบร้อยแล้ว (PID: $(cat "$PID_FILE"))"
        else
            echo "❌ เริ่มระบบไม่สำเร็จ โปรดตรวจสอบ Log: $LOG_FILE"
            cat "$LOG_FILE"
            exit 1
        fi
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            echo "🛑 กำลังหยุดการทำงาน LINE Bot (PID: $PID)..."
            kill "$PID" 2>/dev/null
            rm -f "$PID_FILE"
            echo "✅ หยุดการทำงานเรียบร้อย"
        else
            echo "ℹ️  ไม่พบ PID ของ LINE Bot ที่กำลังทำงาน"
            pkill -f "python3.*app.py" 2>/dev/null
        fi
        ;;
    status)
        if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
            echo "🟢 LINE Bot กำลังทำงานปกติ (PID: $(cat "$PID_FILE"))"
            curl -s http://127.0.0.1:8080/health | jq . 2>/dev/null || curl -s http://127.0.0.1:8080/health
            echo ""
        else
            echo "🔴 LINE Bot ไม่ได้ทำงานอยู่"
        fi
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    logs)
        tail -n 30 -f "$LOG_FILE"
        ;;
    *)
        echo "การใช้งาน: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
