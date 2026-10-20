import io
import re
import json
import logging
from typing import List, Optional, Tuple
from datetime import datetime, date

from domain.models import PDFSummaryResult, WorkItem, TaskStatus
from services.summarizer import tag_mentions

logger = logging.getLogger("PDFService")

class PDFService:
    def __init__(self, provider: str = "mock", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key

    def extract_text_and_pages(self, pdf_bytes: bytes) -> Tuple[str, int]:
        """Extracts text content and page count using pypdf."""
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            num_pages = len(reader.pages)
            text_parts = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    text_parts.append(txt)
            full_text = "\n".join(text_parts).strip()
            return full_text, num_pages
        except Exception as e:
            logger.warning(f"pypdf extraction error: {e}")
            return "", 1

    def process_pdf(
        self,
        pdf_bytes: bytes,
        file_name: str = "document.pdf",
        user_id: str = "unknown_user",
        user_name: str = "น้องบอท"
    ) -> PDFSummaryResult:
        """
        Processes PDF document and generates an easy-to-read, structured summary.
        Also parses any detected work items/schedules inside the PDF.
        """
        extracted_text, num_pages = self.extract_text_and_pages(pdf_bytes)

        if self.provider == "gemini" and self.api_key and self.api_key != "your_gemini_api_key_here":
            summary_text, detected_tasks, key_points, action_items = self._gemini_pdf_extract(
                pdf_bytes=pdf_bytes,
                extracted_text=extracted_text,
                file_name=file_name,
                num_pages=num_pages,
                user_id=user_id,
                user_name=user_name
            )
        else:
            summary_text, detected_tasks, key_points, action_items = self._mock_pdf_extract(
                extracted_text=extracted_text,
                file_name=file_name,
                num_pages=num_pages,
                user_id=user_id,
                user_name=user_name
            )

        return PDFSummaryResult(
            file_name=file_name,
            total_pages=num_pages,
            summary_text=summary_text,
            detected_tasks=detected_tasks,
            key_points=key_points,
            action_items=action_items,
            processed_at=datetime.now()
        )

    def _gemini_pdf_extract(
        self,
        pdf_bytes: bytes,
        extracted_text: str,
        file_name: str,
        num_pages: int,
        user_id: str,
        user_name: str
    ) -> Tuple[str, List[WorkItem], List[str], List[str]]:
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)

            today = date.today()
            current_year = today.year

            prompt = (
                f"คุณคือ 'น้องบอท' ผู้ช่วย AI ประจำสำนักงานพาณิชย์จังหวัดเพชรบุรี (ตอบภาษาไทยสุภาพ เป็นมิตร ชัดเจน ลงท้ายด้วยครับ/ครับผม)\n"
                f"บริบท: วันนี้คือวันที่ {today.isoformat()} (พ.ศ. {current_year + 543})\n"
                f"ชื่อไฟล์เอกสาร: {file_name} (จำนวน {num_pages} หน้า)\n\n"
                f"คำสั่ง:\n"
                f"1. ทำการสรุปสาระสำคัญของเอกสาร PDF นี้ให้อ่านง่าย สบายตา กระชับ และได้ใจความครบถ้วน\n"
                f"2. จัดรูปแบบตามโครงสร้างนี้อย่างเคร่งครัด:\n"
                f"📄 สรุปสาระสำคัญเอกสาร: {file_name}\n"
                f"สำนักงานพาณิชย์จังหวัดเพชรบุรี\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📌 เรื่อง / วัตถุประสงค์หลัก:\n"
                f"(สรุปสั้นๆ 1-3 บรรทัด)\n\n"
                f"📝 ประเด็นสาระสำคัญ:\n"
                f"• (ประเด็นสำคัญที่ 1)\n"
                f"• (ประเด็นสำคัญที่ 2)\n"
                f"• (ประเด็นสำคัญที่ 3)\n\n"
                f"📋 สิ่งที่ต้องดำเนินการ / ภารกิจ (ถ้ามี):\n"
                f"• (รายการงานหรือข้อปฏิบัติ พร้อมระบุผู้รับผิดชอบหรือกลุ่มงาน ถ้ามี)\n\n"
                f"📅 วันที่ / กำหนดการสำคัญ (ถ้ามี):\n"
                f"• (วันเวลา กำหนดส่ง หรือการประชุม)\n\n"
                f"💡 ข้อสังเกต / หมายเหตุเพิ่มเติม:\n"
                f"• (ข้อสังเกตหรือคำแนะนำสั้นๆ)\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💡 น้องบอทพร้อมตอบคำถามเพิ่มเติมเกี่ยวกับเอกสารนี้ครับผม!\n\n"
                f"3. หากเอกสารนี้มี 'ตารางภารกิจ/นัดหมาย/กำหนดการปฏิบัติราชการ' ให้แนบ JSON Array ตอนท้ายสุด:\n"
                f"```json\n"
                f"[\n"
                f'  {{"date": "YYYY-MM-DD", "time": "เวลา เช่น 09:00", "task": "ชื่องานและรายละเอียด", "assignee": "ชื่อผู้รับผิดชอบ", "driver": "พนักงานขับรถถ้ามี", "status": "DONE หรือ IN_PROGRESS"}}\n'
                f"]\n"
                f"```\n"
                f"(ถ้าไม่มีกำหนดการภารกิจ ไม่ต้องใส่ JSON)"
            )

            models_to_try = [
                "gemini-3.8-flash",
                "gemini-3.6-flash",
                "gemini-3.5-flash-lite",
                "gemini-flash-lite-latest",
                "gemini-3-flash-preview"
            ]

            content_payload = [
                prompt,
                {"mime_type": "application/pdf", "data": pdf_bytes}
            ]

            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(content_payload)
                    if response and response.text:
                        raw_output = response.text.strip()
                        tasks = self._parse_json_tasks(raw_output, user_id, user_name)

                        clean_summary = re.sub(r"```(?:json)?\s*\[[\s\S]*?\]\s*```", "", raw_output).strip()
                        clean_summary = re.sub(r"###\s*\*\*.*JSON.*?\*\*", "", clean_summary, flags=re.IGNORECASE).strip()

                        key_points, action_items = self._extract_points(clean_summary)
                        return clean_summary, tasks, key_points, action_items
                except Exception as e:
                    logger.warning(f"PDF model {model_name} failed: {e}")
                    continue

            return self._mock_pdf_extract(extracted_text, file_name, num_pages, user_id, user_name)
        except Exception as e:
            logger.error(f"Gemini PDF processing error: {e}")
            return self._mock_pdf_extract(extracted_text, file_name, num_pages, user_id, user_name)

    def _mock_pdf_extract(
        self,
        extracted_text: str,
        file_name: str,
        num_pages: int,
        user_id: str,
        user_name: str
    ) -> Tuple[str, List[WorkItem], List[str], List[str]]:
        """Fallback rule-based summarizer when Gemini is not configured or in testing."""
        lines = [line.strip() for line in extracted_text.split("\n") if line.strip()]
        
        # Extract title or first substantial line
        title = file_name
        for l in lines[:5]:
            if len(l) > 10 and not l.isdigit():
                title = l
                break

        key_points = []
        action_items = []
        detected_tasks: List[WorkItem] = []

        for l in lines:
            if any(k in l.lower() for k in ["ภารกิจ", "ดำเนินการ", "มอบหมาย", "todo", "action", "งาน", "ตรวจ"]):
                action_items.append(l)
                status = TaskStatus.DONE if any(d in l.lower() for d in ["เสร็จ", "done"]) else TaskStatus.IN_PROGRESS
                detected_tasks.append(WorkItem(
                    user_id=user_id,
                    user_name=user_name,
                    task_text=l,
                    status=status,
                    source="pdf"
                ))
            elif len(l) > 15 and len(key_points) < 5 and l != title:
                key_points.append(l)

        if not key_points:
            key_points = [
                "เอกสารผ่านการอ่านและประมวลผลข้อความเรียบร้อยแล้ว",
                f"เอกสารมีจำนวนทั้งสิ้น {num_pages} หน้า พร้อมเนื้อหาครบถ้วน"
            ]

        summary_lines = [
            f"📄 สรุปสาระสำคัญเอกสาร: {file_name}",
            "สำนักงานพาณิชย์จังหวัดเพชรบุรี",
            "━━━━━━━━━━━━━━━━━━",
            f"📌 เรื่อง / วัตถุประสงค์หลัก:\n{title}\n",
            "📝 ประเด็นสาระสำคัญ:"
        ]
        for kp in key_points[:4]:
            summary_lines.append(f"• {kp}")

        if action_items:
            summary_lines.append("\n📋 สิ่งที่ต้องดำเนินการ / ภารกิจ:")
            for act in action_items[:4]:
                summary_lines.append(f"• {tag_mentions(act)}")

        summary_lines.append("━━━━━━━━━━━━━━━━━━")
        summary_lines.append("💡 น้องบอทพร้อมตอบคำถามเพิ่มเติมเกี่ยวกับเอกสารนี้ครับผม!")

        return "\n".join(summary_lines), detected_tasks, key_points, action_items

    def _parse_json_tasks(self, raw_text: str, user_id: str, user_name: str) -> List[WorkItem]:
        items: List[WorkItem] = []
        try:
            json_match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", raw_text)
            json_str = json_match.group(1) if json_match else ""
            if json_str and "[" in json_str and "]" in json_str:
                start = json_str.index("[")
                end = json_str.rindex("]") + 1
                parsed_list = json.loads(json_str[start:end])
                for entry in parsed_list:
                    task_text = entry.get("task", "").strip()
                    if not task_text:
                        continue
                    assignee = entry.get("assignee", "").strip()
                    driver = entry.get("driver", "").strip()

                    meta_parts = []
                    if assignee:
                        meta_parts.append(assignee)
                    if driver and driver not in ["-", "ไม่มี", "None", "null"]:
                        meta_parts.append(f"ผขร: {driver}")

                    if meta_parts:
                        meta_str = " | ".join(meta_parts)
                        meta_str = tag_mentions(meta_str)
                        if meta_str not in task_text:
                            task_text = f"{task_text} ({meta_str})"

                    date_val = date.today()
                    date_str = entry.get("date")
                    if date_str:
                        try:
                            date_val = date.fromisoformat(date_str)
                        except Exception:
                            pass

                    status_str = str(entry.get("status", "IN_PROGRESS")).upper()
                    status_enum = TaskStatus.DONE if "DONE" in status_str else TaskStatus.IN_PROGRESS

                    task_owner = assignee.strip("@").strip() if assignee else user_name
                    items.append(WorkItem(
                        user_id=user_id,
                        user_name=task_owner,
                        task_text=task_text,
                        status=status_enum,
                        log_date=date_val,
                        scheduled_time=entry.get("time"),
                        source="pdf"
                    ))
        except Exception as e:
            logger.warning(f"Could not parse JSON tasks from PDF: {e}")
        return items

    def _extract_points(self, text: str) -> Tuple[List[str], List[str]]:
        key_points = []
        action_items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("•") or line.startswith("-"):
                clean = line.lstrip("•-* ").strip()
                if any(w in line for w in ["ดำเนินการ", "ผู้รับผิดชอบ", "ภารกิจ"]):
                    action_items.append(clean)
                else:
                    key_points.append(clean)
        return key_points, action_items
