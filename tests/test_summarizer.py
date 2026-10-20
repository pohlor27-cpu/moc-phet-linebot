import pytest
from datetime import date
from domain.models import WorkItem, TaskStatus
from services.summarizer import DailySummarizer

def test_generate_daily_report_empty():
    summarizer = DailySummarizer()
    report = summarizer.generate_daily_report([], date(2026, 10, 5))
    assert report.total_users == 0
    assert report.total_tasks == 0
    assert "ยังไม่มีรายการงาน" in report.formatted_line_message

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
    assert "Design DB" in report.formatted_line_message
    assert "Deploy Server" in report.formatted_line_message

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

def test_alphabetical_and_chronological_ordering():
    summarizer = DailySummarizer()
    items = [
        WorkItem(user_id="U3", user_name="คุณสมชาย", task_text="งานวันที่ 10", log_date=date(2026, 10, 10), scheduled_time="14:00"),
        WorkItem(user_id="U3", user_name="คุณสมชาย", task_text="งานวันที่ 5 เช้า", log_date=date(2026, 10, 5), scheduled_time="09:00"),
        WorkItem(user_id="U3", user_name="คุณสมชาย", task_text="งานวันที่ 5 บ่าย", log_date=date(2026, 10, 5), scheduled_time="13:30"),
        WorkItem(user_id="U1", user_name="คุณกรรณิการ์", task_text="งานตรวจตลาด", log_date=date(2026, 10, 6), scheduled_time="10:00"),
        WorkItem(user_id="U2", user_name="คุณชาญ", task_text="ขับรถรับส่งวิทยากร", log_date=date(2026, 10, 5), scheduled_time="08:00"),
    ]

    report = summarizer.generate_daily_report(items, date(2026, 10, 5))
    msg = report.formatted_line_message

    # 1. Names must appear in alphabetical order: คุณกรรณิการ์ -> คุณชาญ -> คุณสมชาย
    idx_kannika = msg.find("คุณกรรณิการ์")
    idx_chan = msg.find("คุณชาญ")
    idx_somchai = msg.find("คุณสมชาย")

    assert idx_kannika != -1 and idx_chan != -1 and idx_somchai != -1
    assert idx_kannika < idx_chan < idx_somchai

    # 2. For คุณสมชาย, tasks must appear in chronological order:
    # 05/10 09:00 -> 05/10 13:30 -> 10/10 14:00
    idx_task_d5_morning = msg.find("งานวันที่ 5 เช้า")
    idx_task_d5_afternoon = msg.find("งานวันที่ 5 บ่าย")
    idx_task_d10 = msg.find("งานวันที่ 10")

    assert idx_task_d5_morning != -1 and idx_task_d5_afternoon != -1 and idx_task_d10 != -1
    assert idx_task_d5_morning < idx_task_d5_afternoon < idx_task_d10

