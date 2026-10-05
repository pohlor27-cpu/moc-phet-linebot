import json
from datetime import date
from fastapi import APIRouter, Header, HTTPException, Request, UploadFile, File, Form
from typing import Optional

from config import config
from domain.models import WorkItem, DailySummaryReport, OCRResult
from storage.repository import WorkLogRepository
from services.ocr_service import OCRService
from services.summarizer import DailySummarizer
from bot.line_client import LineBotClient
from bot.line_handler import LineWebhookHandler

router = APIRouter()

# Initialize core services
repo = WorkLogRepository(db_path=config.db_path)
ocr_service = OCRService(provider=config.ocr_provider, api_key=config.gemini_api_key)
summarizer = DailySummarizer()
line_client = LineBotClient(
    channel_access_token=config.line_channel_access_token,
    channel_secret=config.line_channel_secret
)
webhook_handler = LineWebhookHandler(
    repo=repo,
    ocr_service=ocr_service,
    summarizer=summarizer,
    line_client=line_client,
    channel_secret=config.line_channel_secret
)

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": config.app_name,
        "daily_summary_time": config.daily_summary_time,
        "ocr_provider": config.ocr_provider
    }

@router.post("/callback")
async def line_webhook_callback(
    request: Request
):
    body_bytes = await request.body()
    signature = (
        request.headers.get("x-line-signature")
        or request.headers.get("X-Line-Signature")
        or ""
    )
    
    if not webhook_handler.verify_signature(body_bytes, signature):
        # In case secret mismatch, log warning
        print(f"[LINE Webhook] Warning: Signature mismatch. Received Sig: {signature[:15]}...")
        # If testing or verify button, allow or handle
        if signature:
            raise HTTPException(status_code=400, detail="Invalid LINE Signature")

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
        print(f"[LINE Webhook] Received payload: {len(payload.get('events', []))} events")
        webhook_handler.handle_webhook_payload(payload)
        return {"status": "ok", "events_processed": len(payload.get("events", []))}
    except Exception as e:
        print(f"[LINE Webhook Error]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/summary/today", response_model=DailySummaryReport)
def get_today_summary(target_date: Optional[str] = None):
    query_date = date.fromisoformat(target_date) if target_date else date.today()
    items = repo.get_items_by_date(query_date)
    return summarizer.generate_daily_report(items, query_date)

@router.post("/api/ocr/upload", response_model=OCRResult)
async def direct_ocr_upload(
    file: UploadFile = File(...),
    user_id: str = Form("api_tester"),
    user_name: str = Form("API Tester")
):
    content = await file.read()
    result = ocr_service.process_image(
        image_bytes=content,
        user_id=user_id,
        user_name=user_name,
        image_path=file.filename
    )
    # Save parsed items
    if result.detected_tasks:
        repo.add_work_items_batch(result.detected_tasks)
    return result

@router.post("/api/logs/manual", response_model=WorkItem)
def manual_add_log(item: WorkItem):
    return repo.add_work_item(item)
