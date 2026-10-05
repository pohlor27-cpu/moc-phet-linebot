import pytest
from datetime import date
from domain.models import WorkItem, TaskStatus
from services.summarizer import DailySummarizer

def test_generate_daily_report_empty():
    summarizer = DailySummarizer()
    report = summarizer.generate_daily_report([], date(2026, 10, 5))
    assert report.total_users == 0
    assert report.total_tasks == 0
    assert "ยังไม่มีการบันทึกรายการงาน" in report.formatted_line_message

def test_generate_daily_report_multi_users():
    summarizer = DailySummarizer()
    today = date(2026, 10, 5)
    items = [
        WorkItem(user_id="U1", user_name="Alice", task_text="Design DB", status=TaskStatus.DONE, log_date=today),
        WorkItem(user_id="U1", user_name="Alice", task_text="Implement API", status=TaskStatus.IN_PROGRESS, log_date=today),
        WorkItem(user_id="U2", user_name="Bob", task_text="Write Tests", status=TaskStatus.DONE, log_date=today),
        WorkItem(user_id="U2", user_name="Bob", task_text="Deploy Server", status=TaskStatus.BLOCKER, log_date=today),
    ]
    
    report = summarizer.generate_daily_report(items, today)
    assert report.total_users == 2
    assert report.total_tasks == 4
    assert report.completed_count == 2
    assert report.in_progress_count == 1
    assert report.blocker_count == 1
    
    assert "Alice" in report.formatted_line_message
    assert "Bob" in report.formatted_line_message
    assert "✅ สำเร็จ: 2" in report.formatted_line_message

def test_generate_morning_briefing():
    summarizer = DailySummarizer()
    today = date.today()
    items = [
        WorkItem(user_id="U1", user_name="Alice", task_text="ตรวจตลาดสดเทศบาล", scheduled_time="09:00 - 12:00", log_date=today),
        WorkItem(user_id="U2", user_name="Bob", task_text="ประชุมแผนงานพาณิชย์", scheduled_time="13:30", log_date=today)
    ]
    briefing = summarizer.generate_morning_briefing(items, today)
    assert "ตารางภารกิจประจำวันนี้" in briefing
    assert "ตรวจตลาดสดเทศบาล" in briefing
    assert "ประชุมแผนงานพาณิชย์" in briefing
    assert "09:00 - 12:00" in briefing
