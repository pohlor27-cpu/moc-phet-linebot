import re
import json
import logging
from typing import List, Optional, Tuple
from datetime import datetime, date, timedelta
from domain.models import OCRResult, WorkItem, TaskStatus

logger = logging.getLogger("OCRService")

class OCRService:
    def __init__(self, provider: str = "mock", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key

    def process_image(self, image_bytes: bytes, user_id: str, user_name: str = "น้องบอท", image_path: Optional[str] = None) -> OCRResult:
        """
        Extracts full schedule text from image and automatically parses structured work logs with dates & times.
        """
        if self.provider == "gemini" and self.api_key and self.api_key != "your_gemini_api_key_here":
            full_summary_text, detected_tasks = self._gemini_vision_extract_structured(image_bytes, user_id, user_name, image_path)
        else:
            full_summary_text = self._mock_ocr_extract(image_bytes)
            detected_tasks = self.parse_text_to_work_items(full_summary_text, user_id, user_name, source="ocr", image_path=image_path)

        if not detected_tasks and full_summary_text:
            detected_tasks = self.parse_text_to_work_items(full_summary_text, user_id, user_name, source="ocr", image_path=image_path)

        return OCRResult(
            extracted_text=full_summary_text,
            detected_tasks=detected_tasks,
            confidence=0.95 if full_summary_text else 0.0,
            processed_at=datetime.now()
        )

    def _mock_ocr_extract(self, image_bytes: bytes) -> str:
        try:
            decoded = image_bytes.decode("utf-8", errors="ignore")
            if any(k in decoded for k in ["งาน", "task", "เสร็จ", "กำลังทำ", "ติดปัญหา", "Todo", "Done", "Built", "FastAPI"]):
                return decoded.strip()
        except Exception:
            pass
        return (
            "1. [เสร็จแล้ว] พัฒนาระบบสรุปงาน LINE OA (คุณสมชาย [กลุ่ม ยผ.])\n"
            "2. [กำลังทำ] เชื่อมต่อ OCR Vision API (คุณกรรณิการ์)\n"
            "3. [ติดปัญหา] รออนุมัติ Line Messaging API Token (คุณสมศรี [กลุ่ม กค.])"
        )

    def _gemini_vision_extract_structured(self, image_bytes: bytes, user_id: str, user_name: str, image_path: Optional[str]) -> Tuple[str, List[WorkItem]]:
        try:
            import io
            from PIL import Image
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            image = Image.open(io.BytesIO(image_bytes))
            
            today = date.today()
            current_year = today.year

            prompt = (
                f"คุณคือ 'น้องบอท' ผู้ช่วย AI ประจำสำนักงานพาณิชย์จังหวัดเพชรบุรี (ตอบเป็นภาษาไทยสุภาพ เป็นผู้ชาย ลงท้ายด้วยครับ/ครับผม)\n"
                f"บริบท: วันนี้คือวันที่ {today.isoformat()} (พ.ศ. {current_year + 543})\n\n"
                f"คำสั่งสำคัญ:\n"
                f"1. อ่านตารางงาน/เอกสาร/ตารางนัดหมายทั้งหมดในรูปภาพอย่างละเอียด\n"
                f"2. สรุปรายการภารกิจทั้งหมดในรูปภาพออกมาให้อ่านง่าย ชัดเจน แยกเป็นรายวัน โดยต้องระบุ: วันที่, เวลา, กิจกรรม/สถานที่, และ **ชื่อผู้รับผิดชอบหรือกลุ่มงานไว้ท้ายงานทุกรายการเสมอ** เช่น '(คุณสมศรี [กลุ่ม กค.])'\n"
                f"3. ในตอนท้ายสุดของคำตอบ ให้แนบ JSON Array ของรายการงานทั้งหมดในรูปแบบนี้:\n"
                f"```json\n"
                f"[\n"
                f'  {{"date": "YYYY-MM-DD", "time": "เวลา เช่น 09:00", "task": "ชื่องานและรายละเอียด", "assignee": "ชื่อผู้รับผิดชอบ/กลุ่มงาน", "status": "DONE หรือ IN_PROGRESS"}}\n'
                f"]\n"
                f"```\n"
                f"หมายเหตุ: แปลงวันที่ เช่น '5 ต.ค.', '6 ต.ค. 69' เป็นปี ค.ศ. YYYY-MM-DD (เช่น 2026-10-05, 2026-10-06)"
            )
            
            # Prioritize verified active models with available quota
            models_to_try = [
                "gemini-3.1-flash-lite",
                "gemini-3.6-flash",
                "gemini-3.5-flash-lite",
                "gemini-flash-lite-latest",
                "gemini-3-flash-preview",
                "gemma-4-26b-a4b-it"
            ]
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content([prompt, image])
                    if response and response.text:
                        raw_output = response.text.strip()
                        tasks = self._parse_json_tasks(raw_output, user_id, user_name, image_path)
                        
                        # Clean raw json codeblocks from user reply
                        user_summary_text = re.sub(r"```(?:json)?\s*\[[\s\S]*?\]\s*```", "", raw_output).strip()
                        user_summary_text = re.sub(r"###\s*\*\*.*JSON.*?\*\*", "", user_summary_text, flags=re.IGNORECASE).strip()
                        
                        if not user_summary_text:
                            lines = ["📋 น้องบอทสรุปตารางภารกิจที่พบในรูปภาพให้แล้วครับผม:\n━━━━━━━━━━━━━━━━━━"]
                            for t in tasks:
                                time_str = f"[{t.scheduled_time}] " if t.scheduled_time else ""
                                lines.append(f"• ({t.log_date.strftime('%d/%m')}) {time_str}{t.task_text}")
                            user_summary_text = "\n".join(lines)
                        
                        return user_summary_text, tasks
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    continue
            
            fallback_text = self._mock_ocr_extract(image_bytes)
            return fallback_text, self.parse_text_to_work_items(fallback_text, user_id, user_name, source="ocr", image_path=image_path)
        except Exception as e:
            logger.error(f"Gemini OCR error: {e}")
            fallback_text = self._mock_ocr_extract(image_bytes)
            return fallback_text, self.parse_text_to_work_items(fallback_text, user_id, user_name, source="ocr", image_path=image_path)

    def _parse_json_tasks(self, raw_text: str, user_id: str, user_name: str, image_path: Optional[str]) -> List[WorkItem]:
        items: List[WorkItem] = []
        try:
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
                    
                    assignee = entry.get("assignee", "").strip()
                    if assignee and assignee not in task_text:
                        task_text = f"{task_text} ({assignee})"
                    
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

    def parse_text_to_work_items(self, text: str, user_id: str, user_name: str = "น้องบอท", source: str = "text", image_path: Optional[str] = None) -> List[WorkItem]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        items: List[WorkItem] = []

        for line in lines:
            clean_line = re.sub(r"^(\d+[\.\)]|\-|\*|•)\s*", "", line).strip()
            if not clean_line or clean_line.startswith("📋") or clean_line.startswith("━") or clean_line.startswith("📅"):
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
