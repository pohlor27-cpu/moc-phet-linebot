# LINE OA Daily Work Summarizer & OCR Bot 🤖📊

ระบบ LINE Official Account Chatbot สำหรับ:
1. **บันทึกและสรุปงานประจำวัน (Daily Standup & Summary Report):**
   - รองรับการพิมพ์ข้อความรายงานงาน ทั้งงานที่เสร็จ, กำลังทำ, หรือติดปัญหา (Blocker)
   - สรุปภาพรวมรายบุคคลและทีม พร้อมคำนวณสถิติอัตโนมัติ
   - ตั้งเวลาส่งสรุปงานรวมเข้าห้องแชทอัตโนมัติทุกวัน (เช่น 18:00 น.)
2. **แปลงรูปภาพเป็นข้อความอัตโนมัติ (Automated OCR / Vision):**
   - ส่งรูปภาพกระดาษโน้ต, รายการ To-Do, หรือภาพหน้าจอ
   - ระบบทำการดึงข้อความ (OCR) และสกัดเป็น Task เข้าระบบอัตโนมัติทันที
3. **API & Webhook Endpoints (FastAPI):**
   - `/callback` : LINE Webhook Event Handler
   - `/api/summary/today` : ดูรายงานสรุปประจำวัน
   - `/api/ocr/upload` : อัปโหลดรูปภาพทดสอบ OCR ตรง
   - `/health` : Health Check

---

## สถาปัตยกรรมระบบ (Architecture)
- **Domain Models:** Pydantic (`WorkItem`, `TaskStatus`, `DailySummaryReport`, `OCRResult`)
- **Storage:** SQLite Repository Pattern (`WorkLogRepository`)
- **OCR Engine:** `OCRService` (รองรับ Gemini Vision API / Multimodal / Mock)
- **Scheduler:** APScheduler (`DailySummaryScheduler`)
- **Web Framework:** FastAPI + Uvicorn + LINE Bot SDK v3

---

## การรัน Test Suite
```bash
cd line_daily_bot
pytest -v
```

## การเริ่มรันเซิร์ฟเวอร์
```bash
cd line_daily_bot
python3 app.py
```
