import sqlite3
import os
from datetime import date, datetime
from typing import List, Optional
from domain.models import WorkItem, TaskStatus

class WorkLogRepository:
    def __init__(self, db_path: str = "line_daily_bot.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    user_name TEXT,
                    task_text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    category TEXT,
                    created_at TEXT NOT NULL,
                    log_date TEXT NOT NULL,
                    scheduled_time TEXT,
                    source TEXT NOT NULL,
                    raw_ocr_image_path TEXT
                )
            """)
            # Check if column scheduled_time exists, if not add it
            cursor.execute("PRAGMA table_info(work_items);")
            columns = [row["name"] for row in cursor.fetchall()]
            if "scheduled_time" not in columns:
                cursor.execute("ALTER TABLE work_items ADD COLUMN scheduled_time TEXT;")

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_date ON work_items(log_date);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_date ON work_items(user_id, log_date);
            """)
            conn.commit()

    def add_work_item(self, item: WorkItem) -> WorkItem:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO work_items (
                    user_id, user_name, task_text, status, category,
                    created_at, log_date, scheduled_time, source, raw_ocr_image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.user_id,
                item.user_name,
                item.task_text,
                item.status.value,
                item.category,
                item.created_at.isoformat(),
                item.log_date.isoformat(),
                item.scheduled_time,
                item.source,
                item.raw_ocr_image_path
            ))
            conn.commit()
            item.id = cursor.lastrowid
            return item

    def add_work_items_batch(self, items: List[WorkItem]) -> List[WorkItem]:
        result = []
        for item in items:
            result.append(self.add_work_item(item))
        return result

    def get_items_by_date(self, target_date: date, user_id: Optional[str] = None) -> List[WorkItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM work_items WHERE log_date = ?"
            params = [target_date.isoformat()]
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            query += " ORDER BY id ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                WorkItem(
                    id=row["id"],
                    user_id=row["user_id"],
                    user_name=row["user_name"],
                    task_text=row["task_text"],
                    status=TaskStatus(row["status"]),
                    category=row["category"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    log_date=date.fromisoformat(row["log_date"]),
                    scheduled_time=row["scheduled_time"] if "scheduled_time" in row.keys() else None,
                    source=row["source"],
                    raw_ocr_image_path=row["raw_ocr_image_path"]
                ) for row in rows
            ]

    def clear_all(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_items")
            conn.commit()
