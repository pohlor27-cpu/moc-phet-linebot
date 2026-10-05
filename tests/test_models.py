import pytest
from datetime import date, datetime
from domain.models import TaskStatus, WorkItem, OCRResult, DailySummaryReport, UserDailySummary

def test_task_status_values():
    assert TaskStatus.DONE == "done"
    assert TaskStatus.IN_PROGRESS == "in_progress"
    assert TaskStatus.BLOCKER == "blocker"
    assert TaskStatus.NOTE == "note"

def test_work_item_creation():
    item = WorkItem(
        user_id="U123456",
        user_name="Somchai",
        task_text="Fixed login bug",
        status=TaskStatus.DONE,
        source="text"
    )
    assert item.user_id == "U123456"
    assert item.status == TaskStatus.DONE
    assert item.log_date == date.today()
    assert item.source == "text"

def test_daily_summary_report():
    user_sum = UserDailySummary(
        user_id="U1",
        user_name="John",
        total_tasks=2,
        done_tasks=["Task A"],
        in_progress_tasks=["Task B"]
    )
    report = DailySummaryReport(
        total_users=1,
        total_tasks=2,
        completed_count=1,
        in_progress_count=1,
        user_summaries=[user_sum],
        formatted_line_message="Report test"
    )
    assert report.total_users == 1
    assert report.completed_count == 1
    assert len(report.user_summaries) == 1
