import re
import json
import logging
from typing import List, Optional
from datetime import datetime, date, timedelta
from domain.models import OCRResult, WorkItem, TaskStatus

logger = logging.getLogger("OCRService")

class OCRService:
    def __init__(self, provider: str = "mock", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key

    def process_image(self, image_bytes: bytes, user_id: str, user_name: str = "Anonymous", image_path: Optional[str] = None) -> OCRResult:
        """
        Extracts text from image and automatically parses structured work logs with dates & times.
        """
        if self.provider == "gemini" and self.api_key and self.api_key != "your_gemini_api_key_here":
            raw_text, detected_tasks = self._gemini_vision_extract_structured(image_bytes, user_id, user_name, image_path)
        else:
            raw_text = self._mock_ocr_extract(image_bytes)
            detected_tasks = self.parse_text_to_work_items(raw_text, user_id, user_name, source="ocr", image_path=image_path)

        if not detected_tasks and raw_text:
            detected_tasks = self.parse_text_to_work_items(raw_text, user_id, user_name, source="ocr", image_path=image_path)

        return OCRResult(
            extracted_text=raw_text,
            detected_tasks=detected_tasks,
            confidence=0.95 if raw_text else 0.0,
            processed_at=datetime.now()
        )

    def _mock_ocr_extract(self, image_bytes: bytes) -> str:
        try:
            decoded = image_bytes.decode("utf-8", errors="ignore")
            if any(k in decoded for k in ["งาน", "task", "เสร็จ", "กำลังทำ", "ติดปัญหา", "Todo", "Done"]):
                return decoded.strip()
        except Exception:
            pass
        return (
            "1. [เสร็จแล้ว] พัฒนาระบบสรุปงาน LINE OA\n"
            "2. [กำลังทำ] เชื่อมต่อ OCR Vision API\n"
            "3. [ติดปัญหา] รออนุมัติ Line Messaging API Token"
        )

    def _gemini_vision_extract_structured(self, image_bytes: bytes, user_id: str, user_name: str, image_path: Optional[str]):
        try:
            import io
            from PIL import Image
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            image = Image.open(io.BytesIO(image_bytes))
            
            today = date.today()
            current_year = today.year
            current_month = today.month

            prompt = (
                f"คุณคือผู้เชี่ยวชาญด้าน OCR ถอดข้อความตารางงาน เอกสารราชการ และตารางภารกิจประจำวัน\n"
                f"บริบท: วันนี้คือวันที่ {today.isoformat()} (พ.ศ. {current_year + 543})\n\n"
                f"คำสั่ง:\n"
                f"1. อ่านและถอดข้อความทั้งหมดในรูปภาพให้ครบถ้วน\n"
                f"2. แยกรายการภารกิจแต่ละรายการออกมาในรูปแบบ JSON Array ต่อไปนี้ (ห้ามใส่ Markdown อื่นนอกจาก JSON block):\n"
                f"```json\n"
                f"[\n"
                f'  {{"date": "YYYY-MM-DD", "time": "HH:MM หรือ ช่วงเวลา", "task": "รายละเอียดภารกิจ/กิจกรรม", "status": "DONE หรือ IN_PROGRESS หรือ BLOCKER"}}\n'
                f"]\n"
                f"```\n"
                f"หมายเหตุเรื่องวันที่: หากในตารางระบุวันที่ เช่น '5 ต.ค.', '6 ต.ค. 69' ให้แปลงเป็น ค.ศ. (YYYY-MM-DD) ให้ถูกต้อง เช่น '2026-10-05', '2026-10-06' หากไม่ระบุวันที่ ให้ใช้วันที่วันนี้ ({today.isoformat()})"
            )
            
            models_to_try = ["gemini-flash-latest", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content([prompt, image])
                    if response and response.text:
                        raw_output = response.text.strip()
                        tasks = self._parse_json_tasks(raw_output, user_id, user_name, image_path)
                        
                        # Generate clean readable summary for Line reply
                        clean_lines = []
                        for t in tasks:
                            time_str = f"[{t.scheduled_time}] " if t.scheduled_time else ""
                            date_str = f"({t.log_date.strftime('%d/%m')}) " if t.log_date != today else ""
                            clean_lines.append(f"• {date_str}{time_str}{t.task_text}")
                        
                        readable_text = "\n".join(clean_lines) if clean_lines else raw_output
                        return readable_text, tasks
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower() or "not found" in str(e).lower():
                        continue
                    logger.warning(f"Model {model_name} error: {e}")
            
            fallback_text = self._mock_ocr_extract(image_bytes)
            return fallback_text, self.parse_text_to_work_items(fallback_text, user_id, user_name, source="ocr", image_path=image_path)
        except Exception as e:
            logger.error(f"Gemini OCR error: {e}")
            fallback_text = self._mock_ocr_extract(image_bytes)
            return fallback_text, self.parse_text_to_work_items(fallback_text, user_id, user_name, source="ocr", image_path=image_path)

    def _parse_json_tasks(self, raw_text: str, user_id: str, user_name: str, image_path: Optional[str]) -> List[WorkItem]:
        items: List[WorkItem] = []
        try:
            # Extract JSON block
            json_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", raw_text)
            json_str = json_match.group(1) if json_match else raw_text
            if "[" in json_str and "]" in json_str:
                start = json_str.index("[")
                end = json_str.rindex("]") + 1
                parsed_list = json.loads(json_str[start:end])
                for entry in parsed_list:
                    task_text = entry.get("task", "").strip()
                    if not task_text:
                        continue
                    
                    date_val = date.today()
                    date_str = entry.get("date")
                    if date_str:
                        try:
                            date_val = date.fromisoformat(date_str)
                        except Exception:
                            pass
                    
                    status_str = str(entry.get("status", "DONE")).upper()
                    status_enum = TaskStatus.DONE
                    if "PROGRESS" in status_str:
                        status_enum = TaskStatus.IN_PROGRESS
                    elif "BLOCK" in status_str or "ERROR" in status_str:
                        status_enum = TaskStatus.BLOCKER

                    items.append(WorkItem(
                        user_id=user_id,
                        user_name=user_name,
                        task_text=task_text,
                        status=status_enum,
                        log_date=date_val,
                        scheduled_time=entry.get("time"),
                        source="ocr",
                        raw_ocr_image_path=image_path
                    ))
        except Exception as e:
            logger.warning(f"Could not parse JSON tasks from OCR: {e}")
        return items

    def parse_text_to_work_items(self, text: str, user_id: str, user_name: str = "Anonymous", source: str = "text", image_path: Optional[str] = None) -> List[WorkItem]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        items: List[WorkItem] = []

        for line in lines:
            clean_line = re.sub(r"^(\d+[\.\)]|\-|\*|•)\s*", "", line).strip()
            if not clean_line:
                continue

            status = self._detect_task_status(clean_line)
            clean_text = re.sub(
                r"^\[(เสร็จแล้ว|done|กำลังทำ|in progress|ติดปัญหา|blocker|note|บันทึก)\]\s*",
                "",
                clean_line,
                flags=re.IGNORECASE
            ).strip()

            items.append(WorkItem(
                user_id=user_id,
                user_name=user_name,
                task_text=clean_text or clean_line,
                status=status,
                log_date=date.today(),
                source=source,
                raw_ocr_image_path=image_path
            ))

        return items

    def _detect_task_status(self, text: str) -> TaskStatus:
        lower = text.lower()
        if any(k in lower for k in ["[ติดปัญหา]", "[blocker]", "blocker", "ติดปัญหา", "error", "bug", "บล็อกเกอร์", "รอ"]):
            return TaskStatus.BLOCKER
        elif any(k in lower for k in ["[กำลังทำ]", "[in progress]", "in progress", "กำลังทำ", "doing", "wip", "อยู่ระหว่าง"]):
            return TaskStatus.IN_PROGRESS
        elif any(k in lower for k in ["[note]", "[บันทึก]", "note:", "บันทึก:"]):
            return TaskStatus.NOTE
        else:
            return TaskStatus.DONE
