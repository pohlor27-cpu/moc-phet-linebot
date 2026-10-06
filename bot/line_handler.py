import re
import hmac
import hashlib
import base64
import logging
from datetime import date, timedelta
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

        # Auto register group ID for broadcast / schedule push
        if group_id:
            self.repo.register_group(group_id)

        if event_type == "join":
            welcome_msg = (
                "👋 สวัสดีครับผม! น้องบอทพร้อมช่วยงานสำนักงานพาณิชย์จังหวัดเพชรบุรีแล้วครับ\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "📌 วิธีใช้งานง่ายๆ:\n"
                "• ส่งรูปถ่ายตารางงาน ➡️ น้องบอทจะสรุปและบันทึกข้อมูลเข้าระบบให้ทันทีครับ\n"
                "• พิมพ์ 'วันนี้' ➡️ ดูตารางภารกิจประจำวันนี้\n"
                "• พิมพ์ 'พรุ่งนี้' ➡️ ดูตารางภารกิจประจำวันพรุ่งนี้\n"
                "• พิมพ์ 'สรุป' ➡️ ดูสรุปผลงานรวม"
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

        # Normalize text and strip leading symbols like /, @, #, !, space
        clean_cmd = re.sub(r"^[!/@#\s]+", "", lower_text).strip()

        # 1. Tomorrow's Schedule ("พรุ่งนี้", "พรุ่งน", "พุ่งนี้")
        if any(clean_cmd == k or clean_cmd.startswith(k) for k in ["พรุ่งนี้", "พรุ่งนี", "พรุ่งน", "พุ่งนี้", "ตารางพรุ่งนี้", "ตารางพรุ่งน", "งานพรุ่งนี้", "ภารกิจพรุ่งนี้", "tomorrow"]) and len(clean_cmd) <= 25:
            tomorrow = date.today() + timedelta(days=1)
            items = self.repo.get_items_by_date(tomorrow)
            briefing = self.summarizer.generate_morning_briefing(items, tomorrow)
            self.line_client.reply_text(reply_token, briefing)
            return

        # 2. Today's Schedule ("วันนี้", "วันน", "วันนี", "ว้นนี้", "ตาราง", "ภารกิจ")
        today_keywords = ["วันนี้", "วันน", "วันนี", "วันนิ", "ว้นนี้", "ตารางวันนี้", "ตารางวันน", "งานวันนี้", "งานวันน", "ตารางงาน", "ตาราง", "ภารกิจ", "today", "schedule"]
        if (any(clean_cmd == k for k in today_keywords) or (any(clean_cmd.startswith(k) for k in today_keywords) and len(clean_cmd) <= 20 and "@" not in lower_text)):
            today = date.today()
            items = self.repo.get_items_by_date(today)
            briefing = self.summarizer.generate_morning_briefing(items, today)
            self.line_client.reply_text(reply_token, briefing)
            return

        # 3. Summary ("สรุป", "สรป", "สรุปงาน")
        if any(clean_cmd == k or clean_cmd.startswith(k) for k in ["สรุป", "สรป", "สรุปงาน", "สรุปวันน", "สรุปวันนี้", "รายงาน", "summary"]) and len(clean_cmd) <= 20:
            today = date.today()
            items = self.repo.get_items_by_date(today)
            report = self.summarizer.generate_daily_report(items, today)
            self.line_client.reply_text(reply_token, report.formatted_line_message)
            return

        # 4. Yesterday's Summary ("เมื่อวาน", "เมื่อวานนี้")
        if any(clean_cmd == k or clean_cmd.startswith(k) for k in ["เมื่อวาน", "เมื่อวานนี้", "เมื่อวานน", "สรุปเมื่อวาน", "งานเมื่อวาน", "yesterday"]) and len(clean_cmd) <= 20:
            yesterday = date.today() - timedelta(days=1)
            items = self.repo.get_items_by_date(yesterday)
            report = self.summarizer.generate_daily_report(items, yesterday)
            self.line_client.reply_text(reply_token, report.formatted_line_message)
            return

        # 5. Help & Guide ("เมนู", "วิธีใช้", "คำสั่ง")
        if any(clean_cmd == k for k in ["help", "start", "วิธีใช้", "?", "เมนู", "คำสั่ง", "คู่มือ"]):
            help_msg = (
                "🤖 น้องบอท (พาณิชย์จังหวัดเพชรบุรี)\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "• พิมพ์ 'วันนี้' หรือ 'วันน' ➡️ ดูตารางงานวันนี้\n"
                "• พิมพ์ 'พรุ่งนี้' ➡️ ดูตารางงานวันพรุ่งนี้\n"
                "• พิมพ์ 'สรุป' ➡️ ดูสรุปผลงานรวม\n"
                "• ส่งรูปตารางงาน ➡️ น้องบอทจะสรุปและบันทึกอัตโนมัติครับผม"
            )
            self.line_client.reply_text(reply_token, help_msg)
            return

        # 6. Greeting / Bot Status
        if any(clean_cmd == k for k in ["บอท", "bot", "เทส", "test", "สวัสดี", "น้องบอท", "hi", "hello"]):
            msg = (
                "👋 น้องบอทพร้อมทำงานครับผม!\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "• พิมพ์ 'วันนี้' ➡️ ดูตารางภารกิจวันนี้\n"
                "• พิมพ์ 'พรุ่งนี้' ➡️ ดูตารางภารกิจวันพรุ่งนี้\n"
                "• ส่งรูปถ่ายตารางงาน เพื่อให้น้องบอทสรุปและบันทึกได้เลยครับ ✨"
            )
            self.line_client.reply_text(reply_token, msg)
            return

        # Note: Do NOT reply or add tasks for random captions / general group chats
        logger.info(f"Ignoring general non-command text: '{text[:50]}'")

    def _handle_image_message(self, reply_token: Optional[str], user_id: str, user_name: str, message_id: str):
        if not reply_token:
            return

        # 1. Fetch image bytes from Line API
        image_bytes = self.line_client.get_message_content(message_id)

        # 2. Extract full schedule summary & parse tasks via OCR Service
        ocr_result = self.ocr_service.process_image(
            image_bytes=image_bytes,
            user_id=user_id,
            user_name=user_name
        )

        extracted = ocr_result.extracted_text.strip()
        if not extracted or extracted == "[NON_SCHEDULE_IMAGE]":
            logger.info("Ignoring non-schedule image (silent mode)")
            return

        if extracted.startswith("[Error"):
            self.line_client.reply_text(
                reply_token,
                "⚠️ น้องบอทไม่สามารถอ่านข้อความจากรูปภาพนี้ได้ กรุณาลองส่งใหม่อีกครั้งนะครับผม"
            )
            return

        # 3. Save structured tasks to database
        if ocr_result.detected_tasks:
            self.repo.add_work_items_batch(ocr_result.detected_tasks)

        # 4. Return full schedule summary extracted from the image
        reply_lines = [
            extracted,
            "",
            "━━━━━━━━━━━━━━━━━━",
            f"✅ น้องบอทบันทึกตารางภารกิจเข้าระบบเรียบร้อยแล้วครับผม ({len(ocr_result.detected_tasks)} รายการ)",
            "💡 พิมพ์ 'วันนี้' หรือ 'พรุ่งนี้' เพื่อดูภารกิจเฉพาะวันได้เลยครับ"
        ]
        self.line_client.reply_text(reply_token, "\n".join(reply_lines).strip())
