import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from config import config
from api.routes import router, repo, summarizer, line_client
from services.scheduler import DailySummaryScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("App")

scheduler = DailySummaryScheduler(
    morning_time=config.morning_schedule_time,
    evening_time=config.daily_summary_time,
    timezone_str=config.timezone
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {config.app_name}...")
    # Start background scheduler for daily summary push
    scheduler.start(
        broadcast_callback=line_client.broadcast_summary,
        repo=repo,
        summarizer=summarizer
    )
    yield
    logger.info("Shutting down...")
    scheduler.stop()

app = FastAPI(
    title=config.app_name,
    description="Line OA Chatbot for Daily Work Summary, Standup aggregation, and Image-to-Text OCR",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.host, port=config.port, reload=True)
