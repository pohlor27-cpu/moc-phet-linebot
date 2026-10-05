import re
from typing import List, Optional
from datetime import datetime, date
from domain.models import OCRResult, WorkItem, TaskStatus

class OCRService:
    def __init__(self, provider: str = "mock", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key

    def process_image(self, image_bytes: bytes, user_id: str, user_name: str = "Anonymous", image_path: Optional[str] = None) -> OCRResult:
        """
        Extracts text from image and automatically parses work logs.
        """
        if self.provider == "gemini" and self.api_key and self.api_key != "your_gemini_api_key_here":
            raw_text = self._gemini_vision_extract(image_bytes)
        else:
            raw_text = self._mock_ocr_extract(image_bytes)

        # Parse extracted text into structured WorkItems
        detected_tasks = self.parse_text_to_work_items(
            text=raw_text,
            user_id=user_id,
            user_name=user_name,
            source="ocr",
            image_path=image_path
        )

        return OCRResult(
            extracted_text=raw_text,
            detected_tasks=detected_tasks,
            confidence=0.95 if raw_text else 0.0,
            processed_at=datetime.now()
        )

    def _mock_ocr_extract(self, image_bytes: bytes) -> str:
        # If payload contains utf-8 text or fallback mock text
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

    def _gemini_vision_extract(self, image_bytes: bytes) -> str:
        try:
            import io
            from PIL import Image
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            image = Image.open(io.BytesIO(image_bytes))
            prompt = "โปรดอ่านและคัดลอกเฉพาะข้อความทั้งหมดที่ปรากฏในรูปภาพนี้ออกมาเป็นภาษาไทยหรืออังกฤษอย่างถูกต้อง โดยไม่ต้องใส่คำอธิบายเพิ่มเติม"
            
            # Try available flash models
            models_to_try = ["gemini-flash-latest", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content([prompt, image])
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower() or "not found" in str(e).lower():
                        continue
                    raise e
            return "[ระบบกำลังประมวลผลรูปภาพ กรุณาลองใหม่อีกครั้ง]"
        except Exception as e:
            return self._mock_ocr_extract(image_bytes)

    def parse_text_to_work_items(self, text: str, user_id: str, user_name: str = "Anonymous", source: str = "text", image_path: Optional[str] = None) -> List[WorkItem]:
        """
        Intelligently parses lines of text into structured WorkItem models with status detection.
        """
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        items: List[WorkItem] = []

        for line in lines:
            # Clean list bullets / numbering (e.g. "1. ", "- ", "* ", "• ")
            clean_line = re.sub(r"^(\d+[\.\)]|\-|\*|•)\s*", "", line).strip()
            if not clean_line:
                continue

            status = self._detect_task_status(clean_line)
            
            # Clean status prefixes from text
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
            # Default to Done if marked done or typical report format
            return TaskStatus.DONE
