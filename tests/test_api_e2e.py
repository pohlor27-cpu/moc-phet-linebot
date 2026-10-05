import pytest
import io
from fastapi.testclient import TestClient
from app import app
from domain.models import TaskStatus

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_webhook_post():
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "test_reply_token",
                "source": {"userId": "U_TEST", "displayName": "Tester"},
                "message": {"type": "text", "text": "1. ทดสอบระบบ API\n2. [กำลังทำ] เขียน E2E Test"}
            }
        ]
    }
    response = client.post("/callback", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_summary_api():
    response = client.get("/api/summary/today")
    assert response.status_code == 200
    data = response.json()
    assert "report_date" in data
    assert "total_tasks" in data
    assert "formatted_line_message" in data

def test_ocr_upload_api():
    fake_image_file = io.BytesIO(b"1. [Done] Manual OCR File Upload\n2. [In Progress] Verify Status")
    response = client.post(
        "/api/ocr/upload",
        files={"file": ("test_doc.jpg", fake_image_file, "image/jpeg")},
        data={"user_id": "U_OCR_TEST", "user_name": "OCR User"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["detected_tasks"]) == 2
    assert data["detected_tasks"][0]["task_text"] == "Manual OCR File Upload"
    assert data["detected_tasks"][0]["status"] == "done"
