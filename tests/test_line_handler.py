import pytest
from datetime import date, timedelta
from domain.models import TaskStatus, WorkItem
from storage.repository import WorkLogRepository
from services.ocr_service import OCRService
from services.summarizer import DailySummarizer
from bot.line_client import LineBotClient
from bot.line_handler import LineWebhookHandler

@pytest.fixture
def setup_handler(tmp_path):
    db_file = str(tmp_path / "test_handler.db")
    repo = WorkLogRepository(db_path=db_file)
    ocr = OCRService(provider="mock")
    summarizer = DailySummarizer()
    client = LineBotClient(channel_access_token="test_token", channel_secret="test_secret")
    handler = LineWebhookHandler(
        repo=repo,
        ocr_service=ocr,
        summarizer=summarizer,
        line_client=client,
        channel_secret="test_secret"
    )
    return handler, repo, client

def test_ignore_general_caption_text(setup_handler):
    handler, repo, client = setup_handler
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "token123",
                "source": {"userId": "U001", "displayName": "Somsak"},
                "message": {"type": "text", "text": "@All ตารางงานวันที่ 3-11 ต.ค. 69 ค่ะ"}
            }
        ]
    }
    handler.handle_webhook_payload(payload)
    
    # Should ignore and not reply or add tasks
    items = repo.get_items_by_date(date.today())
    assert len(items) == 0
    assert len(client.sent_messages) == 0

def test_handle_today_command(setup_handler):
    handler, repo, client = setup_handler
    repo.add_work_item(WorkItem(user_id="U001", user_name="Alice", task_text="ประชุมประจำสัปดาห์", status=TaskStatus.DONE, log_date=date.today()))
    
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "token_today",
                "source": {"userId": "U001"},
                "message": {"type": "text", "text": "วันนี้"}
            }
        ]
    }
    handler.handle_webhook_payload(payload)
    
    assert len(client.sent_messages) == 1
    assert "ตารางภารกิจประจำวันนี้" in client.sent_messages[0]["text"]
    assert "ประชุมประจำสัปดาห์" in client.sent_messages[0]["text"]

def test_handle_tomorrow_command(setup_handler):
    handler, repo, client = setup_handler
    tomorrow = date.today() + timedelta(days=1)
    repo.add_work_item(WorkItem(user_id="U001", user_name="Alice", task_text="ลงพื้นที่ตรวจตลาด", status=TaskStatus.DONE, log_date=tomorrow))
    
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "token_tomorrow",
                "source": {"userId": "U001"},
                "message": {"type": "text", "text": "พรุ่งนี้"}
            }
        ]
    }
    handler.handle_webhook_payload(payload)
    
    assert len(client.sent_messages) == 1
    assert "ตารางภารกิจประจำวันพรุ่งนี้" in client.sent_messages[0]["text"]
    assert "ลงพื้นที่ตรวจตลาด" in client.sent_messages[0]["text"]

def test_handle_summary_command(setup_handler):
    handler, repo, client = setup_handler
    repo.add_work_item(WorkItem(user_id="U001", user_name="Somsak", task_text="Work A", status=TaskStatus.DONE, log_date=date.today()))
    
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "token_sum",
                "source": {"userId": "U001"},
                "message": {"type": "text", "text": "สรุป"}
            }
        ]
    }
    handler.handle_webhook_payload(payload)
    
    assert len(client.sent_messages) == 1
    assert "สรุปผลงานประจำวันนี้" in client.sent_messages[0]["text"]
    assert "Work A" in client.sent_messages[0]["text"]

def test_handle_image_ocr(setup_handler):
    handler, repo, client = setup_handler
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "token_img",
                "source": {"userId": "U002", "displayName": "Nok"},
                "message": {"type": "image", "id": "msg_img_999"}
            }
        ]
    }
    handler.handle_webhook_payload(payload)
    
    items = repo.get_items_by_date(date.today())
    assert len(items) > 0
    assert len(client.sent_messages) == 1
    assert "น้องบอทบันทึกตารางภารกิจเข้าระบบเรียบร้อยแล้วครับผม" in client.sent_messages[0]["text"]
