import io
import pytest
import pypdf
from fastapi.testclient import TestClient

from app import app
from services.pdf_service import PDFService
from bot.line_client import LineBotClient
from bot.line_handler import LineWebhookHandler
from storage.repository import WorkLogRepository
from services.ocr_service import OCRService
from services.summarizer import DailySummarizer

def create_sample_pdf(text_lines):
    writer = pypdf.PdfWriter()
    # Create page with blank background and add text
    page = writer.add_blank_page(width=400, height=500)
    # pypdf can write metadata
    writer.add_metadata({"/Title": "บันทึกข้อความราชการ"})
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()

def test_pdf_service_mock_process():
    service = PDFService(provider="mock")
    # Generate dummy PDF bytes
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=400)
    stream = io.BytesIO()
    writer.write(stream)
    pdf_bytes = stream.getvalue()

    result = service.process_pdf(
        pdf_bytes=pdf_bytes,
        file_name="ตารางภารกิจประจำสัปดาห์.pdf",
        user_id="Utest",
        user_name="คุณสมชาย"
    )

    assert result.file_name == "ตารางภารกิจประจำสัปดาห์.pdf"
    assert result.total_pages >= 1
    assert "📄 สรุปสาระสำคัญเอกสาร" in result.summary_text
    assert "สำนักงานพาณิชย์จังหวัดเพชรบุรี" in result.summary_text
    assert "━━━━━━━━━━━━━━━━━━" in result.summary_text
    assert "💡 น้องบอทพร้อมตอบคำถามเพิ่มเติม" in result.summary_text

def test_line_handler_file_message():
    repo = WorkLogRepository("test_pdf.db")
    repo.clear_all()
    ocr = OCRService(provider="mock")
    pdf_service = PDFService(provider="mock")
    summarizer = DailySummarizer()
    client = LineBotClient("dummy_token", "dummy_secret")

    handler = LineWebhookHandler(
        repo=repo,
        ocr_service=ocr,
        summarizer=summarizer,
        line_client=client,
        channel_secret="dummy_secret",
        pdf_service=pdf_service
    )

    # Mock client message content to return valid PDF bytes
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=400)
    stream = io.BytesIO()
    writer.write(stream)
    client.get_message_content = lambda msg_id: stream.getvalue()

    event = {
        "type": "message",
        "replyToken": "reply_token_file_123",
        "source": {"userId": "U_test_user", "displayName": "พี่ป๋อ"},
        "message": {
            "type": "file",
            "id": "file_msg_999",
            "fileName": "รายงานผลการดำเนินงานพาณิชย์.pdf",
            "fileSize": 10240
        }
    }

    handler._process_single_event(event)

    assert len(client.sent_messages) == 1
    sent = client.sent_messages[0]
    assert sent["action"] == "reply"
    assert sent["reply_token"] == "reply_token_file_123"
    assert "รายงานผลการดำเนินงานพาณิชย์.pdf" in sent["text"]

def test_api_pdf_summary_endpoint():
    client = TestClient(app)

    # Generate sample PDF
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=400)
    stream = io.BytesIO()
    writer.write(stream)
    pdf_data = stream.getvalue()

    files = {"file": ("โครงการพาณิชย์ลดราคา.pdf", pdf_data, "application/pdf")}
    response = client.post("/api/pdf/summary", files=files, data={"user_name": "คุณกรรณิการ์"})

    assert response.status_code == 200
    data = response.json()
    assert data["file_name"] == "โครงการพาณิชย์ลดราคา.pdf"
    assert "📄 สรุปสาระสำคัญเอกสาร" in data["summary_text"]

def test_api_ocr_upload_with_pdf():
    client = TestClient(app)

    # Upload PDF to /api/ocr/upload
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=300, height=400)
    stream = io.BytesIO()
    writer.write(stream)
    pdf_data = stream.getvalue()

    files = {"file": ("ประกาศสำนักงานพาณิชย์.pdf", pdf_data, "application/pdf")}
    response = client.post("/api/ocr/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "📄 สรุปสาระสำคัญเอกสาร" in data["extracted_text"]
