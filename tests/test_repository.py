import os
import pytest
from datetime import date
from domain.models import WorkItem, TaskStatus
from storage.repository import WorkLogRepository

@pytest.fixture
def repo(tmp_path):
    db_file = str(tmp_path / "test_bot.db")
    return WorkLogRepository(db_path=db_file)

def test_add_and_get_work_items(repo):
    item1 = WorkItem(
        user_id="U001",
        user_name="Alice",
        task_text="Refactored database module",
        status=TaskStatus.DONE,
        log_date=date.today()
    )
    item2 = WorkItem(
        user_id="U002",
        user_name="Bob",
        task_text="Building frontend UI",
        status=TaskStatus.IN_PROGRESS,
        log_date=date.today()
    )
    
    saved1 = repo.add_work_item(item1)
    saved2 = repo.add_work_item(item2)
    
    assert saved1.id is not None
    assert saved2.id is not None

    items = repo.get_items_by_date(date.today())
    assert len(items) == 2
    assert items[0].task_text == "Refactored database module"
    assert items[1].task_text == "Building frontend UI"

def test_filter_by_user(repo):
    repo.add_work_item(WorkItem(user_id="U001", task_text="Task 1", log_date=date.today()))
    repo.add_work_item(WorkItem(user_id="U002", task_text="Task 2", log_date=date.today()))
    
    user1_items = repo.get_items_by_date(date.today(), user_id="U001")
    assert len(user1_items) == 1
    assert user1_items[0].task_text == "Task 1"
