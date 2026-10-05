import pytest
from datetime import date
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

def test_handle_text_log(setup_handler):
    handler, repo, client = setup_handler
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "token123",
                "source": {"userId": "U001", "displayName": "Somsak"},
                "message": {"type": "text", "text": "1. ทำหน้าบ้านเสร็จแล้ว\n2. [กำลังทำ] ต่อ API"}
            }
        ]
    }
    handler.handle_webhook_payload(payload)
    
    items = repo.get_items_by_date(date.today())
    assert len(items) == 2
    assert items[0].task_text == "ทำหน้าบ้านเสร็จแล้ว"
    assert items[1].status == TaskStatus.IN_PROGRESS
    
    assert len(client.sent_messages) == 1
    assert "บันทึกงานเรียบร้อยแล้ว" in client.sent_messages[0]["text"]

def test_handle_summary_command(setup_handler):
    handler, repo, client = setup_handler
    repo.add_work_item(WorkItem(user_id="U001", user_name="Somsak", task_text="Work A", status=TaskStatus.DONE, log_date=date.today()))
    
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "token_sum",
                "source": {"userId": "U001"},
                "message": {"type": "text", "text": "/summary"}
            }
        ]
    }
    handler.handle_webhook_payload(payload)
    
    assert len(client.sent_messages) == 1
    assert "สรุปงานประจำวัน" in client.sent_messages[0]["text"]
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
    assert "บันทึกข้อมูลตารางงานเรียบร้อยแล้วครับ" in client.sent_messages[0]["text"]
