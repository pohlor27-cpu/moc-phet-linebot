import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

class AppConfig(BaseModel):
    app_name: str = "LINE OA Daily Work Summarizer & OCR Bot"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))
    
    # LINE OA Credentials
    line_channel_secret: str = os.getenv("LINE_CHANNEL_SECRET", "dummy_channel_secret")
    line_channel_access_token: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy_channel_access_token")
    
    # Database
    db_path: str = os.getenv("DB_PATH", "line_daily_bot.db")
    
    # Scheduler Times (24h format HH:MM)
    morning_schedule_time: str = os.getenv("MORNING_SCHEDULE_TIME", "07:30")  # แจ้งตารางงานเช้า
    daily_summary_time: str = os.getenv("DAILY_SUMMARY_TIME", "17:05")       # สรุปงานเย็น
    timezone: str = os.getenv("TIMEZONE", "Asia/Bangkok")
    
    # OCR Provider (mock, gemini, or vision)
    ocr_provider: str = os.getenv("OCR_PROVIDER", "gemini")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

config = AppConfig()
