from datetime import datetime, date
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    DONE = "done"               # งานที่เสร็จแล้ว
    IN_PROGRESS = "in_progress" # งานที่กำลังดำเนินการ
    BLOCKER = "blocker"         # ติดปัญหา / บล็อกเกอร์
    NOTE = "note"               # บันทึกทั่วไป

class WorkItem(BaseModel):
    id: Optional[int] = None
    user_id: str
    user_name: Optional[str] = "Anonymous"
    task_text: str
    status: TaskStatus = TaskStatus.DONE
    category: Optional[str] = "General"
    created_at: datetime = Field(default_factory=datetime.now)
    log_date: date = Field(default_factory=date.today)
    scheduled_time: Optional[str] = None  # e.g. "09:00", "09:00 - 12:00", "ช่วงเช้า"
    source: str = "text"  # "text" or "ocr"
    raw_ocr_image_path: Optional[str] = None

class OCRResult(BaseModel):
    extracted_text: str
    detected_tasks: List[WorkItem] = Field(default_factory=list)
    confidence: float = 1.0
    language: str = "th+en"
    processed_at: datetime = Field(default_factory=datetime.now)

class UserDailySummary(BaseModel):
    user_id: str
    user_name: str
    total_tasks: int
    done_tasks: List[str] = Field(default_factory=list)
    in_progress_tasks: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

class DailySummaryReport(BaseModel):
    report_date: date = Field(default_factory=date.today)
    total_users: int = 0
    total_tasks: int = 0
    completed_count: int = 0
    in_progress_count: int = 0
    blocker_count: int = 0
    user_summaries: List[UserDailySummary] = Field(default_factory=list)
    formatted_line_message: str = ""
