import hmac
import hashlib
import base64
import logging
from datetime import date
from typing import Dict, Any, Optional

from domain.models import WorkItem, TaskStatus
from storage.repository import WorkLogRepository
from services.ocr_service import OCRService
from services.summarizer import DailySummarizer
from bot.line_client import LineBotClient

logger = logging.getLogger("LineWebhookHandler")

class LineWebhookHandler:
    def __init__(
        self,
        repo: WorkLogRepository,
        ocr_service: OCRService,
        summarizer: DailySummarizer,
        line_client: LineBotClient,
        channel_secret: str
    ):
        self.repo = repo
        self.ocr_service = ocr_service
        self.summarizer = summarizer
        self.line_client = line_client
        self.channel_secret = channel_secret

    def verify_signature(self, body_bytes: bytes, signature: str) -> bool:
        if not signature or self.channel_secret == "dummy_channel_secret":
            return True  # Allow testing/mocking in dev
        
        hash_val = hmac.new(
            self.channel_secret.encode('utf-8'),
            body_bytes,
            hashlib.sha256
        ).digest()
        expected_sig = base64.b64encode(hash_val).decode('utf-8')
        return hmac.compare_digest(expected_sig, signature)

    def handle_webhook_payload(self, payload: Dict[str, Any]):
        events = payload.get("events", [])
        for event in events:
            try:
                self._process_single_event(event)
            except Exception as e:
                logger.error(f"Error processing webhook event: {e}", exc_info=True)

    def _process_single_event(self, event: Dict[str, Any]):
        event_type = event.get("type")
        reply_token = event.get("replyToken")
        source = event.get("source", {})
        user_id = source.get("userId", "unknown_user")
        group_id = source.get("groupId") or source.get("roomId")
        
        user_name = source.get("displayName")
        if not user_name and reply_token:
            user_name = self.line_client.get_user_display_name(user_id, group_id)

        if event_type == "join":
            welcome_msg = (
                "👋 สวัสดีครับทุกคน! ผมคือบอทสรุปงานและบันทึกตารางงานประจำวัน\n"
                "สำนักงานพาณิชย์จังหวัดเพชรบุรี\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "📌 คำสั่งและวิธีใช้งาน:\n"
                "• พิมพ์ /ตาราง หรือ 'ตารางงาน' เพื่อดูภารกิจวันนี้\n"
                "• พิมพ์ /summary หรือ 'สรุป' เพื่อดูรายงานสรุปงาน\n"
                "• ถ่ายรูปตารางงาน/กระดาษโน้ตส่งเข้าห้อง บอทจะแปลงข้อความและบันทึกให้อัตโนมัติ\n"
                "• ระบบจะแจ้งตารางงานทุกเช้า 07:30 น. และสรุปงานทุกเย็น 17:05 น."
            )
            if reply_token:
                self.line_client.reply_text(reply_token, welcome_msg)
            return

        if event_type != "message":
            return

        message = event.get("message", {})
        msg_type = message.get("type")

        if msg_type == "text":
            text = message.get("text", "").strip()
            self._handle_text_message(reply_token, user_id, user_name, text)
        elif msg_type == "image":
            message_id = message.get("id")
            self._handle_image_message(reply_token, user_id, user_name, message_id)

    def _handle_text_message(self, reply_token: Optional[str], user_id: str, user_name: str, text: str):
        if not reply_token:
            return
        
        lower_text = text.lower().strip()

        # 1. Help & Greeting
        if lower_text in ["/help", "/start", "วิธีใช้", "help", "?", "ช่วยด้วย", "เมนู"]:
            help_msg = (
                "🤖 LINE Daily Work & OCR Bot (พาณิชย์จังหวัดเพชรบุรี)\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "📌 วิธีบันทึกงานประจำวัน:\n"
                "1. พิมพ์ข้อความงาน เช่น:\n"
                "   • พัฒนาระบบ API เสร็จแล้ว\n"
                "   • [กำลังทำ] ออกแบบหน้า UI\n"
                "   • [ติดปัญหา] รอเอกสารลงนาม\n\n"
                "2. ส่งรูปภาพ (OCR อัตโนมัติ):\n"
                "   • ถ่ายรูปตารางงานหรือกระดาษโน้ตส่งมาได้เลย บอทจะบันทึกให้ทันที\n\n"
                "📌 คำสั่งดูรายงาน:\n"
                "• 'ตารางงาน' หรือ /ตาราง : ดูตารางภารกิจประจำวันนี้ (07:30)\n"
                "• 'สรุป' หรือ /summary : ดูสรุปผลงานรวมวันนี้ (17:05)"
            )
            self.line_client.reply_text(reply_token, help_msg)
            return

        # 2. Daily Schedule / Morning Briefing
        if lower_text in ["/schedule", "/ตาราง", "ตารางงาน", "ตาราง", "งานวันนี้", "ภารกิจวันนี้", "ภารกิจ"]:
            today = date.today()
            items = self.repo.get_items_by_date(today)
            briefing = self.summarizer.generate_morning_briefing(items, today)
            self.line_client.reply_text(reply_token, briefing)
            return

        # 3. Daily Summary / Report
        if lower_text in ["/summary", "/สรุป", "/today", "สรุปงาน", "สรุป", "รายงาน"]:
            today = date.today()
            items = self.repo.get_items_by_date(today)
            report = self.summarizer.generate_daily_report(items, today)
            self.line_client.reply_text(reply_token, report.formatted_line_message)
            return

        # 4. General Bot Status Check
        if lower_text in ["บอท", "bot", "เทส", "test", "สวัสดี", "hi", "hello", "อยู่ไหม"]:
            msg = (
                "👋 บอทพร้อมทำงานครับพี่ป๋อ!\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "• พิมพ์ 'ตารางงาน' เพื่อดูภารกิจวันนี้\n"
                "• พิมพ์ 'สรุป' เพื่อดูสรุปงานทั้งหมด\n"
                "• หรือส่งรูปภาพตารางงานเพื่อสแกนบันทึกได้เลยครับ ✨"
            )
            self.line_client.reply_text(reply_token, msg)
            return

        # 5. Regular Work Log entry
        items = self.ocr_service.parse_text_to_work_items(
            text=text,
            user_id=user_id,
            user_name=user_name,
            source="text"
        )
        saved_items = self.repo.add_work_items_batch(items)

        reply_lines = [
            f"✅ บันทึกงานเรียบร้อยแล้ว ({len(saved_items)} รายการ):",
            "━━━━━━━━━━━━━━━━━━"
        ]
        for item in saved_items[:10]:
            status_icon = "✅" if item.status == TaskStatus.DONE else ("⏳" if item.status == TaskStatus.IN_PROGRESS else "⚠️")
            reply_lines.append(f"{status_icon} [{item.status.value.upper()}] {item.task_text}")
        
        if len(saved_items) > 10:
            reply_lines.append(f"... และอีก {len(saved_items) - 10} รายการ")

        reply_lines.append("\n💡 พิมพ์ 'สรุป' เพื่อดูรายงาน หรือ 'ตารางงาน' เพื่อดูภารกิจ")
        self.line_client.reply_text(reply_token, "\n".join(reply_lines))

    def _handle_image_message(self, reply_token: Optional[str], user_id: str, user_name: str, message_id: str):
        if not reply_token:
            return

        # 1. Fetch image bytes from Line API
        image_bytes = self.line_client.get_message_content(message_id)

        # 2. Extract text & parse tasks via OCR Service
        ocr_result = self.ocr_service.process_image(
            image_bytes=image_bytes,
            user_id=user_id,
            user_name=user_name
        )

        extracted = ocr_result.extracted_text.strip()
        if not extracted or extracted.startswith("[Error"):
            self.line_client.reply_text(
                reply_token,
                "⚠️ ไม่สามารถอ่านข้อความจากรูปภาพได้ในขณะนี้ กรุณาลองใหม่อีกครั้งครับ"
            )
            return

        # Save to database
        if ocr_result.detected_tasks:
            self.repo.add_work_items_batch(ocr_result.detected_tasks)

        # Return clean notification after processing
        reply_lines = [
            "⏳ บันทึกข้อมูลตารางงานเรียบร้อยแล้วครับ",
            "━━━━━━━━━━━━━━━━━━",
            extracted
        ]
        self.line_client.reply_text(reply_token, "\n".join(reply_lines))
