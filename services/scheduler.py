import logging
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Callable, Optional

logger = logging.getLogger("SchedulerService")

class DailySummaryScheduler:
    def __init__(
        self,
        morning_time: str = "07:30",
        evening_time: str = "17:05",
        timezone_str: str = "Asia/Bangkok"
    ):
        self.morning_time = morning_time
        self.evening_time = evening_time
        self.timezone_str = timezone_str
        self.scheduler = BackgroundScheduler(timezone=timezone_str)

    def start(self, broadcast_callback: Callable[[str], None], repo, summarizer):
        # 1. Morning Daily Schedule Briefing (07:30)
        m_hour, m_minute = map(int, self.morning_time.split(":"))
        def morning_job():
            logger.info("Executing scheduled morning daily briefing job...")
            today = date.today()
            items = repo.get_items_by_date(today)
            briefing_msg = summarizer.generate_morning_briefing(items, today)
            group_ids = repo.get_registered_groups()
            broadcast_callback(briefing_msg, group_ids=group_ids)

        m_trigger = CronTrigger(hour=m_hour, minute=m_minute, timezone=self.timezone_str)
        self.scheduler.add_job(
            morning_job,
            trigger=m_trigger,
            id="morning_briefing_push",
            replace_existing=True
        )

        # 2. Evening Daily Summary Wrapup (17:05)
        e_hour, e_minute = map(int, self.evening_time.split(":"))
        def evening_job():
            logger.info("Executing scheduled evening daily summary job...")
            today = date.today()
            items = repo.get_items_by_date(today)
            report = summarizer.generate_daily_report(items, today)
            group_ids = repo.get_registered_groups()
            broadcast_callback(report.formatted_line_message, group_ids=group_ids)

        e_trigger = CronTrigger(hour=e_hour, minute=e_minute, timezone=self.timezone_str)
        self.scheduler.add_job(
            evening_job,
            trigger=e_trigger,
            id="evening_summary_push",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(f"Morning briefing scheduled for {self.morning_time}, Evening summary for {self.evening_time} ({self.timezone_str})")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped.")
